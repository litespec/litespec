"""``verify-ec``: layered equivalence checking (Phase 8).

Runs the five seam obligations (C↔LIR, LIR↔Unsafe, Unsafe↔Safe, LIR↔ISIR,
Safe↔ISIR) on one or more C functions and records the refinement chain
``T_C ⊑ T_LIR ⊑ T_Unsafe ⊑ T_Safe ⊑_α T_ISIR``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from litespec.equivalence import verify_function
from litespec.type_mapping import load_type_model


def verify_ec_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="litespec verify-ec",
        description="Layered equivalence checking (Phase 8)",
    )
    parser.add_argument("file", help="path to a .c source file")
    parser.add_argument("--function", "-f", action="append", dest="functions", help="function to verify (repeatable)")
    parser.add_argument("--all", action="store_true", help="verify every function in the file")
    parser.add_argument("--type-model", default="liteos")
    args = parser.parse_args(argv)

    src = Path(args.file).read_bytes()
    tm = load_type_model(args.type_model)

    if args.all:
        from litespec.extraction import parse_c
        from litespec.extraction.c_translation_unit import functions

        fns = sorted({f.name for f in functions(parse_c(src)) if f.name})
    else:
        fns = args.functions or ["LOS_MemAlloc", "LOS_MemFree"]

    failed = 0
    passed = 0
    for name in fns:
        result, chain = verify_function(src, name, type_model=tm)
        if result.status == "pass":
            passed += 1
        elif result.status == "fail":
            failed += 1
        print(f"[{result.status.upper()}] {name}")
        for r in result.reports:
            print(f"      {r}")
        for e in result.errors:
            print(f"      error: {e}")
        for w in result.warnings:
            print(f"      warn: {w}")
        print(f"      chain: {', '.join(chain.links)}")

    print(f"verify-ec: {passed} passed, {failed} failed, {len(fns) - passed - failed} warned")
    return 1 if failed else 0
