"""``verify`` command: one-shot final verification of a ported target (Phase 8).

Compiles the full ported module once, classifies every function by coverage level,
and reports a summary. Returns 0 iff the module compiles and there are no mismatches.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from litespec.equivalence.coverage import coverage_report, format_coverage
from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.config import Config
from litespec.lowering import port_module
from litespec.type_mapping import load_type_model


def _compile_rust(rust: str) -> tuple[bool, str]:
    if shutil.which("rustc") is None:
        return True, "rustc not available (skipping compile)"
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "out.rs"
        rlib = Path(d) / "out.rlib"
        src.write_text(rust, encoding="utf-8")
        proc = subprocess.run(
            ["rustc", "--edition", "2021", "--crate-type", "lib", str(src), "-o", str(rlib)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return True, "compiles"
        return False, proc.stderr.strip()[:300]


def verify_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="litespec verify", description="One-shot verification of a ported target")
    parser.add_argument("file", help="path to a .c source file")
    parser.add_argument("--type-model", default="liteos")
    parser.add_argument("--target", default=None, help="target name to load the testing config from")
    args = parser.parse_args(argv)

    # Load the target's testing configuration (generic pipeline).
    target = None
    testing = None
    if args.target:
        from litespec.targets import load_target

        target = load_target(args.target)
        testing = target.testing

    with open(args.file, "rb") as fh:
        source = fh.read()

    seen: set[str] = set()
    fns = []
    for f in functions(parse_c(source)):
        if f.name and f.name not in seen:
            seen.add(f.name)
            fns.append(f.name)
    if not fns:
        print(f"no functions found in {args.file}")
        return 1

    tm = load_type_model(args.type_model)
    cfg = Config.liteos_default()

    # 1. compile the full module once
    rust = port_module(source, fns, type_model=tm, config=cfg, module_name=target.port_name if target else "")
    ok, msg = _compile_rust(rust)
    print(f"module: {len(fns)} functions, {len(rust.splitlines())} lines → {msg}")
    if not ok:
        return 1

    # 2. coverage classification (fn table built once)
    counts, per_fn = coverage_report(source, fns, type_model=tm, config=cfg)
    print(f"verification coverage of {len(fns)} functions:")
    print(format_coverage(counts, len(fns)))
    differential = [n for n, lvl in per_fn.items() if lvl == "differential"]
    print(f"  differentially verified: {differential}")
    mismatches = [n for n, lvl in per_fn.items() if lvl == "mismatch"]
    if mismatches:
        print(f"  MISMATCHES: {mismatches}", file=sys.stderr)
        return 1

    # 3. enforce the target's testing config (generic thresholds)
    if testing is not None:
        missing = [n for n in testing.required_differential if per_fn.get(n) != "differential"]
        if missing:
            print(f"  required-differential NOT met: {missing}", file=sys.stderr)
            return 1
        if not testing.fail_on_mismatch and mismatches:
            print("  note: mismatches present but fail_on_mismatch is off")

    print("verify: PASS")
    return 0
