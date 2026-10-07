"""``coverage`` command: report verification coverage of a target's functions (Phase 8)."""

from __future__ import annotations

import argparse

from litespec.equivalence.coverage import coverage_report, format_coverage
from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.config import Config
from litespec.type_mapping import load_type_model


def coverage_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="litespec coverage", description="Report verification coverage")
    parser.add_argument("file", help="path to a .c source file")
    parser.add_argument("--type-model", default="liteos")
    args = parser.parse_args(argv)

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
    counts, per_fn = coverage_report(source, fns, type_model=tm, config=cfg)
    print(f"verification coverage of {len(fns)} functions:")
    print(format_coverage(counts, len(fns)))
    differential = [n for n, lvl in per_fn.items() if lvl == "differential"]
    print(f"  differentially verified: {differential}")
    mismatches = [n for n, lvl in per_fn.items() if lvl == "mismatch"]
    if mismatches:
        print(f"  MISMATCHES: {mismatches}")
        return 1
    return 0
