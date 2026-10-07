"""``generate-tests`` command: emit an auto-generated pytest module (Phase 8)."""

from __future__ import annotations

import argparse

from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.verification import generate_tests


def generate_tests_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="litespec generate-tests", description="Generate a pytest module for a target's functions"
    )
    parser.add_argument("file", help="path to a .c source file")
    parser.add_argument("-o", "--output", default=None, help="write to this path (default: stdout)")
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

    text = generate_tests(args.file, fns)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {len(fns)} function tests to {args.output}")
    else:
        print(text)
    return 0
