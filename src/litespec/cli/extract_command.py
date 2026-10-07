"""``extract`` command: C → LIR extraction (Phase 2)."""

from __future__ import annotations

import argparse
import sys

from litespec.extraction import collect_loop_analyses, extract_function
from litespec.extraction.c_parser import parse_c
from litespec.extraction.c_translation_unit import functions


def extract_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="litespec extract", description="Extract C to LIR")
    parser.add_argument("file", help="path to a .c file")
    args = parser.parse_args(argv)

    with open(args.file, "rb") as fh:
        source = fh.read()

    tu = parse_c(source)
    fns = functions(tu)
    if not fns:
        print(f"no functions found in {args.file}", file=sys.stderr)
        return 1

    for cfn in fns:
        fn = extract_function(source, cfn.name)
        loops = collect_loop_analyses(fn.effect, fn.name)
        print(f"# {fn.name} -> {fn.return_type}")
        print(f"  parameters: {[(n, t) for n, t in fn.parameters]}")
        print(f"  state_vars: {fn.state_vars}")
        print(f"  loops: {[str(l.loop_kind) for l in loops]}")
        print(f"  effect: {fn.effect!r}")
        print()
    return 0
