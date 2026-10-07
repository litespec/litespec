#!/usr/bin/env python3
"""Generate the single-file "combined" LiteOS-A sources used by the integration tests.

The ``tests/integration/test_liteos_a_*.py`` suite reads hand-curated, single-file
versions of the real LiteOS-A sources (e.g. ``/tmp/los_memory_a.c``). Those files are
produced by *include-inlining*: local ``#include "..."`` headers are expanded in place
(recursively, deduplicated), while system includes (``<...>``) and unresolvable paths are
dropped. Crucially, ``#define`` / ``#if`` / ``#ifdef`` directives are left intact so the
extractor's own macro resolver and preprocessor-branch selector can do their job — unlike
``clang -E -P``, which would erase the ``#define`` lines the tests rely on.

A header contributes *types, macros, and extern declarations* plus the inline helper
functions that the module actually calls. Header function definitions that are not
reachable from the module's own ``.c`` file (the scheduler/timer/atomic helpers pulled in
via the shared ``los_config.h``/arch closure) are stripped, so the ported module does not
drag the whole kernel's 64-bit timer/atomic code into every combined file.

Usage:
    ./run.sh generate-combined        # regenerate every module into /tmp
    ./run.sh generate-combined kernel_mm
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from litespec.extraction.c_parser import parse_c
from litespec.extraction.c_translation_unit import _function_name, functions

REPO = Path(__file__).resolve().parents[1]
KERNEL = REPO / "third_party" / "liteos"
BOARD = REPO / ".tools" / "board" / "include"
STUBS = REPO / ".tools" / "stubs" / "include"

INCLUDE_DIRS = [
    KERNEL / "kernel" / "include",
    KERNEL / "kernel" / "base" / "include",
    KERNEL / "kernel" / "common",
    KERNEL / "arch" / "arm" / "include",
    KERNEL / "arch" / "arm" / "arm" / "include",
    KERNEL / "arch" / "arm" / "arm" / "src" / "include",
    KERNEL / "lib" / "libscrew" / "include",
    BOARD,
    STUBS,
    KERNEL,
]

INCLUDE_RE = re.compile(r'^(\s*)#\s*include\s*([<"])([^>"]+)[>"]\s*$')
# Empty section/attribute/storage macros (``LITE_OS_SEC_*``, ``WEAK``, ``STATIC``,
# ``INLINE``, ``EXTERN``) decorate symbols; stripping them keeps tree-sitter from
# mis-parsing declarations like ``STATIC LOS_DL_LIST g_unusedSemList;``.
ATTR_MACRO_RE = re.compile(
    r"\b(?:LITE_OS_SEC_\w+|STATIC_INLINE|STATIC|INLINE|EXTERN|WEAK|USED|NORETURN|DEPRECATED)\b"
)

_DEFINE_RE = re.compile(r"^#\s*define\s+([A-Za-z_]\w*)\b\s*(.*)$")
_UNDEF_RE = re.compile(r"^#\s*undef\s+([A-Za-z_]\w*)")


class _PP:
    """Tracks ``#if``/``#ifdef``/``#ifndef`` nesting during include-inlining.

    Only the active branch's lines (``#define``, ``#include``, declarations) are
    emitted, so tree-sitter never sees the unbalanced braces of a ``#ifdef`` that
    wraps part of a statement (e.g. ``#ifdef SMP / if (…) { / #endif / return;``).
    """

    def __init__(self, config):
        self.config = config
        self.stack: list[list] = []  # [parent_active, any_branch_taken]
        self.active = True

    def push(self, cond: bool) -> None:
        self.stack.append([self.active, cond])
        self.active = self.active and cond

    def elif_(self, cond: bool) -> None:
        if not self.stack:
            return
        frame = self.stack[-1]
        if not frame[1]:
            frame[1] = cond
            self.active = frame[0] and cond
        else:
            self.active = False

    def else_(self) -> None:
        if not self.stack:
            return
        frame = self.stack[-1]
        if not frame[1]:
            frame[1] = True
            self.active = frame[0]
        else:
            self.active = False

    def endif(self) -> None:
        if self.stack:
            frame = self.stack.pop()
            self.active = frame[0]

    def note_define(self, line: str) -> None:
        """Record an object-like ``#define`` so later ``#ifdef``/``#if`` see it."""
        m = _DEFINE_RE.match(line)
        if not m:
            return
        name, value = m.group(1), m.group(2).strip()
        self.config.defined.add(name)
        if name.startswith("__") or name.startswith("LOSCFG_") is False and "(" in value:
            pass
        num = re.match(r"([+-]?0[xX][0-9A-Fa-f]+|[+-]?[0-9]+)", value)
        if num:
            try:
                self.config.values[name] = int(num.group(1), 0)
            except ValueError:
                pass


def _pp_config():
    """Preprocessor config: target ``preprocess.defines`` + compiler builtins."""
    from litespec.extraction.config import Config
    from litespec.targets.loader import load_target

    t = load_target("liteos")
    defined = set(t.preprocess_defines.keys())
    defined.add("__GNUC__")  # clang/gcc (IAR's __ICCARM__ stays undefined)
    values: dict[str, int] = {}
    for k, v in t.preprocess_defines.items():
        try:
            values[k] = int(v)
        except (ValueError, TypeError):
            pass
    return Config(defined=defined, values=values)

# module -> (output basename, [source files])  (source files relative to KERNEL)
MODULES: dict[str, tuple[str, list[str]]] = {
    "kernel_mm": ("los_memory_a.c", ["kernel/base/mem/tlsf/los_memory.c"]),
    "bitmap": ("los_bitmap_combined.c", ["kernel/base/core/los_bitmap.c"]),
    "mux": ("los_mux_combined.c", ["kernel/base/ipc/los_mux.c"]),
    "event": ("los_event_combined.c", ["kernel/base/ipc/los_event.c"]),
    "queue": ("los_queue_combined.c", ["kernel/base/ipc/los_queue.c"]),
    "sem": ("los_sem_combined.c", ["kernel/base/ipc/los_sem.c"]),
    "sys": ("los_sys_combined.c", ["kernel/base/core/los_sys.c"]),
    "swtmr": ("los_swtmr_combined.c", ["kernel/base/core/los_swtmr.c"]),
    "sched": ("los_sched_combined.c", ["kernel/base/sched/los_sched.c"]),
    "pm": ("los_pm_combined.c", ["kernel/extended/power/los_pm.c"]),
    "task": ("los_task_combined.c", ["kernel/base/core/los_task.c"]),
    "list": ("los_list_combined.c", ["kernel/include/los_list.h"]),
    "arch_mmu": ("los_arch_mmu_combined.c", ["arch/arm/arm/src/los_arch_mmu.c"]),
}


def resolve(name: str, current: Path) -> Path | None:
    """Resolve an include name against the current file's dir, then the include dirs."""
    candidates = [current.parent / name] + [d / name for d in INCLUDE_DIRS]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _body_call_names(body) -> set[str]:
    """Names called inside a function body (tree-sitter ``call_expression``)."""
    names: set[str] = set()
    if body is None:
        return names

    def walk(n) -> None:
        if n.type == "call_expression":
            fn = n.child_by_field_name("function")
            if fn is not None:
                if fn.type == "identifier":
                    names.add(fn.text.decode())
                elif fn.type == "field_expression":
                    field = fn.child_by_field_name("field")
                    if field is not None:
                        names.add(field.text.decode())
        for c in n.named_children:
            walk(c)

    walk(body)
    return names


def _file_function_calls(path: Path) -> dict[str, set[str]]:
    """Function name → called names, for every function *defined* in a file."""
    out: dict[str, set[str]] = {}
    try:
        tu = parse_c(path.read_bytes())
    except Exception:
        return out
    for f in functions(tu):
        if f.name:
            out[f.name] = _body_call_names(f.body)
    return out


def _closure(sources: list[Path]) -> list[Path]:
    """Resolve the .c file + all transitively-included headers (DFS, deduplicated)."""
    order: list[Path] = []
    seen: set[Path] = set()

    def visit(path: Path) -> None:
        rp = path.resolve()
        if rp in seen:
            return
        seen.add(rp)
        order.append(rp)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        for raw in text.splitlines():
            m = INCLUDE_RE.match(raw)
            if m:
                inc = resolve(m.group(3), path)
                if inc is not None:
                    visit(inc)

    for s in sources:
        visit(s)
    return order


def _reachable(files: list[Path]) -> set[str]:
    """Function names reachable from the module's own ``.c`` files (transitively)."""
    calls = {f: _file_function_calls(f) for f in files}
    roots = set()
    for src in files:
        if src.suffix == ".c":
            roots |= set(calls[src])
    reachable = set(roots)
    changed = True
    while changed:
        changed = False
        for f in files:  # all files: .c roots and headers alike
            for name, callees in calls.get(f, {}).items():
                if name in reachable:
                    for c in callees:
                        if c not in reachable:
                            reachable.add(c)
                            changed = True
    return reachable


def _strip_unreachable(text: str, reachable: set[str]) -> str:
    """Remove header function *definitions* that are not reachable from the module."""
    try:
        root = parse_c(text)
    except Exception:
        return text
    ranges: list[tuple[int, int]] = []

    def walk(n) -> None:
        if n.type == "function_definition":
            if _function_name(n) not in reachable:
                ranges.append((n.start_byte, n.end_byte))
        for c in n.named_children:
            walk(c)

    walk(root)
    for start, end in sorted(ranges, reverse=True):
        text = text[:start] + text[end:]
    return text


def inline(path: Path, seen: set[Path], out: list[str], reachable: set[str], pp: _PP, is_header: bool = False) -> None:
    from litespec.extraction.config import eval_pp_condition

    rp = path.resolve()
    if rp in seen:
        return
    seen.add(rp)
    text = path.read_text(encoding="utf-8", errors="replace")
    if is_header:
        text = _strip_unreachable(text, reachable)
    for raw in text.splitlines():
        stripped = raw.lstrip()
        # Resolve conditional-compilation directives (only the active branch emits).
        if stripped.startswith("#ifdef "):
            pp.push(pp.config.is_defined(stripped[len("#ifdef ") :].strip()))
            continue
        if stripped.startswith("#ifndef "):
            pp.push(not pp.config.is_defined(stripped[len("#ifndef ") :].strip()))
            continue
        if stripped.startswith("#if "):
            pp.push(eval_pp_condition(stripped[len("#if ") :].strip(), pp.config))
            continue
        if stripped.startswith("#elif "):
            pp.elif_(eval_pp_condition(stripped[len("#elif ") :].strip(), pp.config))
            continue
        if stripped.startswith("#else"):
            pp.else_()
            continue
        if stripped.startswith("#endif"):
            pp.endif()
            continue
        if not pp.active:
            continue
        # Track object-like #define / #undef for later conditionals.
        if stripped.startswith("#define "):
            pp.note_define(stripped)
            out.append(raw)
            continue
        m_undef = _UNDEF_RE.match(stripped)
        if m_undef:
            pp.config.defined.discard(m_undef.group(1))
            continue
        # Strip attribute/storage macros from usage sites (declarations, bodies), but
        # never from ``#define``/``#if``/``#include`` lines — those define the macros.
        if not raw.lstrip().startswith("#"):
            raw = ATTR_MACRO_RE.sub("", raw)
        m = INCLUDE_RE.match(raw)
        if m:
            inc = resolve(m.group(3), path)
            if inc is not None:
                inline(inc, seen, out, reachable, pp, is_header=True)
            # else: drop system / unresolvable include
        else:
            out.append(raw)


def generate(module: str, dest_dir: Path | None = None) -> Path:
    if module not in MODULES:
        raise SystemExit(f"unknown module {module!r}; choose from {sorted(MODULES)}")
    basename, sources = MODULES[module]
    src_paths = [KERNEL / rel for rel in sources]
    for src in src_paths:
        if not src.is_file():
            raise SystemExit(f"missing source {src} (run ./run.sh fetch-source liteos)")

    files = _closure(src_paths)
    reachable = _reachable(files)

    pp = _PP(_pp_config())
    out_lines: list[str] = []
    seen: set[Path] = set()
    for src in src_paths:
        # The module's own source files (whether .c or .h, e.g. los_list.h) are
        # inlined in full; only transitively-included headers are pruned.
        inline(src, seen, out_lines, reachable, pp, is_header=False)

    dest = (dest_dir or Path("/tmp")) / basename
    dest.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return dest


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate combined LiteOS-A sources")
    parser.add_argument("module", nargs="?", help="module name (default: all)")
    parser.add_argument("--out", default="/tmp", help="output directory")
    args = parser.parse_args(argv)

    modules = [args.module] if args.module else list(MODULES)
    for mod in modules:
        dest = generate(mod, Path(args.out))
        print(f"{mod}: {dest} ({dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
