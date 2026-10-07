"""Differential verification: compile C and compare its behavior to the LIR (Phase 8).

For an *interpretable* (pure) function, build a self-contained C harness (typedefs,
macros, the function, and a ``main``), compile it with ``clang``, run it on bounded
concrete inputs, and compare the observed outputs against the LIR interpreter under
C's unsigned-wrapping semantics. This turns the ``c_to_lir`` seam into a real
observational-equivalence check on the pure fragment.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from litespec.equivalence.lir_interp import concrete_inputs, is_interpretable, run_effect, set_fn_table
from litespec.extraction.c_translation_unit import _function_name
from litespec.extraction.macro_table import MacroTable


def build_c_preamble(tm=None, empty_macros=None) -> str:
    """Generate the reference-C preamble from the type model + intrinsics table.

    Typedefs come from ``tm.c_typedefs``; intrinsic macros come from
    ``litespec.intrinsics`` (via ``c_macro``); empty macros (section attributes)
    come from the target config's ``preprocess.empty_macros``. The preamble cannot
    drift from the pipeline's own tables.
    """
    from litespec.intrinsics import INTRINSICS, c_macro, register_mmio_from_target
    from litespec.targets.loader import load_target
    from litespec.type_mapping import load_type_model

    # The pipeline's default target is LiteOS; fall back to its type model + config
    # so the preamble carries the LiteOS typedefs (UINT32, …) and section macros.
    tm = tm or load_type_model("liteos")
    if empty_macros is None:
        empty_macros = load_target("liteos").preprocess_empty_macros
    register_mmio_from_target()
    lines = [f"typedef {c_type} {name};" for name, c_type in sorted(tm.c_typedefs.items())]
    lines += ["#define STATIC static", "#define INLINE inline", "#define NULL 0"]
    for name, intr in INTRINSICS.items():
        macro = c_macro(name, intr)
        if macro is not None:
            lines.append(macro)
    for name in empty_macros:
        lines.append(f"#define {name}")
    return "\n".join(lines) + "\n"


def unsigned_bits(return_type: str) -> int | None:
    """Unsigned width to wrap to (None = unbounded), matching C integer promotion."""
    if "UINT8" in return_type:
        return 8
    if "UINT16" in return_type:
        return 16
    if "UINT32" in return_type or return_type.strip() in ("BOOL", "UINT", "INT"):
        return 32
    if "UINT64" in return_type or return_type.strip() in ("SIZE_T",):
        return 64
    return None  # pointers / void / unknown → no wrap


def _function_definition(tu, name):
    def walk(node):
        if node.type == "function_definition" and _function_name(node) == name:
            return node
        for child in node.named_children:
            found = walk(child)
            if found is not None:
                return found
        return None

    return walk(tu)


def _callees(effect) -> set[str]:
    from litespec.lir.effect_expr_ast import Call, CallEffect

    out: set[str] = set()

    def walk(e) -> None:
        if isinstance(e, (Call, CallEffect)):
            out.add(e.name)
            for a in getattr(e, "args", ()):
                walk(a)
        for attr in (
            "left",
            "right",
            "operand",
            "base",
            "index",
            "cond",
            "then",
            "else_",
            "expr",
            "init",
            "step",
            "body",
        ):
            child = getattr(e, attr, None)
            if child is not None:
                walk(child)
        for item in getattr(e, "items", ()):
            walk(item)

    walk(effect)
    return out


def _call_closure(fn_table: dict, name: str) -> list[str]:
    """Topological order of ported functions reachable from ``name`` (callees first)."""
    order: list[str] = []
    visited: set[str] = set()

    def dfs(n: str) -> None:
        if n in visited:
            return
        visited.add(n)
        for callee in _callees(fn_table[n][1]):
            if callee in fn_table:
                dfs(callee)
        order.append(n)

    dfs(name)
    return order


def build_c_harness(
    c_source: bytes | str, names: list[str], param_names: list[str], tm=None
) -> tuple[str, list[str]] | None:
    """Return ``(harness_text, param_names)`` including the function and its callees."""
    from litespec.extraction import parse_c

    tu = parse_c(c_source)
    fn_texts: list[str] = []
    for name in names:
        fn_def = _function_definition(tu, name)
        if fn_def is None:
            return None
        text = fn_def.text
        fn_texts.append(text.decode("utf-8", "replace") if isinstance(text, bytes) else text)

    mt = MacroTable.from_translation_unit(tu)
    defines = []
    for k, v in sorted(mt.constants.items()):
        if v:
            defines.append(f"#define {k} {v}")
    for k, (params, body) in sorted(mt.functions.items()):
        defines.append(f"#define {k}({', '.join(params)}) ({body})")

    entry = names[-1]  # topological order ends with the entry function
    argv = ", ".join(f"atoll(argv[{i + 1}])" for i in range(len(param_names)))
    main = (
        "#include <stdio.h>\n#include <stdlib.h>\n"
        f"int main(int argc, char **argv) {{\n"
        f'    printf("%llu\\n", (unsigned long long)({entry}({argv})));\n'
        "    return 0;\n"
        "}\n"
    )
    body = build_c_preamble(tm) + "\n" + "\n".join(defines) + "\n" + "\n".join(fn_texts) + "\n" + main
    return body, param_names


def compile_and_run(harness: str, inputs: list[dict[str, int]], param_names: list[str]) -> list[int] | None:
    """Compile the harness and run it on each input tuple; return observed outputs."""
    if shutil.which("clang") is None:
        return None
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "harness.c"
        exe = Path(d) / "harness"
        src.write_text(harness, encoding="utf-8")
        proc = subprocess.run(["clang", "-w", "-O0", str(src), "-o", str(exe)], capture_output=True, text=True)
        if proc.returncode != 0:
            return None
        outputs = []
        for env in inputs:
            args = [str(exe)] + [str(env[n]) for n in param_names]
            run = subprocess.run(args, capture_output=True, text=True)
            if run.returncode != 0:
                return None
            try:
                outputs.append(int(run.stdout.strip()))
            except ValueError:
                return None
        return outputs


def build_fn_table(c_source: bytes | str, config=None) -> dict:
    """Map function name → (param names, effect, return-width bits) for interpretation."""
    from litespec.extraction import extract_function, parse_c
    from litespec.extraction.c_translation_unit import functions

    table: dict = {}
    for f in functions(parse_c(c_source)):
        if not f.name:
            continue
        try:
            fn = extract_function(c_source, f.name, config=config)
        except ValueError:
            continue
        table[f.name] = (tuple(n for n, _ in fn.parameters), fn.effect, unsigned_bits(fn.return_type))
    return table


def differential_check(c_source: bytes | str, lir, fn_table: dict | None = None, tm=None) -> tuple[str, list]:
    """Compare C behavior against the LIR for an interpretable function.

    ``lir`` is the already-extracted ``ExtractedFunction``. Returns
    ``(status, counterexamples)`` where status is ``"ok"``, ``"impure"``
    (structural only), ``"mismatch"``, or ``"unavailable"`` (no clang / no harness).
    """
    name = lir.name
    if fn_table is None:
        fn_table = build_fn_table(c_source)
    set_fn_table(fn_table)

    # Set the interpreter's word mask from the active type model (word_bits).
    if tm is not None and getattr(tm, "word_bits", None):
        from litespec.equivalence.lir_interp import set_word_bits

        set_word_bits(tm.word_bits)

    if not is_interpretable(lir.effect):
        return "impure", []

    param_names = [n for n, _ in lir.parameters]
    closure = _call_closure(fn_table, name)
    built = build_c_harness(c_source, closure, param_names, tm=tm)
    if built is None:
        return "unavailable", []
    harness, _ = built

    inputs = concrete_inputs([(n, "Nat") for n in param_names])
    c_outputs = compile_and_run(harness, inputs, param_names)
    if c_outputs is None:
        return "unavailable", []

    mismatches = []
    bits = unsigned_bits(lir.return_type)
    for env, c_out in zip(inputs, c_outputs):
        lir_out = run_effect(lir.effect, env, bits=bits)
        if lir_out != c_out:
            mismatches.append((dict(env), c_out, lir_out))
    return ("ok" if not mismatches else "mismatch"), mismatches


def differential_check_rust(c_source: bytes | str, name: str, tm=None) -> tuple[str, list]:
    """Compare the *unsafe Rust* output against the LIR interpreter (LIR↔Unsafe).

    For an interpretable (pure) function, lower it to unsafe Rust, run it on bounded
    concrete inputs, and compare each output against the LIR interpreter. This turns
    the ``lir_to_unsafe`` seam into a real observational-equivalence check in Rust
    space (the analog of ``differential_check`` for the C↔LIR seam). Returns
    ``("ok" | "impure" | "mismatch" | "unavailable", counterexamples)``.
    """
    from litespec.equivalence.lir_interp import concrete_inputs, is_interpretable, run_effect
    from litespec.extraction import extract_function
    from litespec.extraction.config import Config
    from litespec.lowering import port_module
    from litespec.type_mapping import load_type_model

    tm = tm or load_type_model("liteos")
    # Set the interpreter's word mask from the active type model (word_bits), so a
    # 64-bit target masks to 64 bits (mirrors differential_check's C↔LIR path).
    from litespec.equivalence.lir_interp import set_word_bits

    if getattr(tm, "word_bits", None):
        set_word_bits(tm.word_bits)

    fn = extract_function(c_source, name, type_model=tm)
    if not is_interpretable(fn.effect):
        return "impure", []

    param_names = [n for n, _ in fn.parameters]
    bits = unsigned_bits(fn.return_type)
    inputs = concrete_inputs([(n, "Nat") for n in param_names])

    # LIR side.
    lir_outputs = [run_effect(fn.effect, dict(env), bits=bits) for env in inputs]

    # Rust side: lower the function + its callee closure (so callees are real, not
    # stubbed), append a main() that prints each output, compile, run.
    closure = _call_closure(build_fn_table(c_source), name)
    rust = port_module(c_source, closure, type_model=tm, config=Config(), executable=True)
    main = "\nfn main() { unsafe {\n"
    for env in inputs:
        args = ", ".join(str(env[n]) for n in param_names)
        main += f'  println!("{{}}", {name}({args}));\n'
    main += "} }\n"
    rust += main

    with tempfile.TemporaryDirectory() as d:
        srcf = Path(d) / "rust_diff.rs"
        exe = Path(d) / "rust_diff"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        if proc.returncode != 0:
            return "unavailable", [proc.stderr.strip()[-300:]]
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        if run.returncode != 0:
            return "unavailable", [run.stderr.strip()[-300:]]
        rust_outputs = [int(tok) for tok in run.stdout.split()]

    mismatches = []
    for env, lir_out, rust_out in zip(inputs, lir_outputs, rust_outputs):
        if lir_out != rust_out:
            mismatches.append((dict(env), rust_out, lir_out))
    return ("ok" if not mismatches else "mismatch"), mismatches
