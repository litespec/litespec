"""``validate`` command: load and dump a ``.litespec.yaml`` document."""

from __future__ import annotations

import argparse
import sys

from litespec.serialization import dump_litespec, load_litespec


def validate_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="litespec validate", description="Validate a .litespec.yaml")
    parser.add_argument("file", help="path to a .litespec.yaml file")
    parser.add_argument("--dump", action="store_true", help="print the re-serialized document")
    args = parser.parse_args(argv)

    try:
        doc = load_litespec(args.file)
    except Exception as exc:  # noqa: BLE001 - report any load error
        print(f"validation failed: {args.file}: {exc}", file=sys.stderr)
        return 1

    n_specs = len(doc.specs)
    print(f"OK: {args.file} ({n_specs} spec(s), litespec_version={doc.litespec_version})")

    if args.dump:
        print(dump_litespec(doc))
    return 0
