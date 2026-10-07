"""``fetch-source`` command: retrieve the target source from its config."""

from __future__ import annotations

import argparse
import sys

from litespec.targets import available_targets, fetch_source, load_target, resolve_target


def fetch_source_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="litespec fetch-source", description="Retrieve the target source")
    parser.add_argument("target", nargs="?", default=None, help="target name (config/targets/<name>.yaml)")
    args = parser.parse_args(argv)

    target_name = resolve_target(args.target)
    if target_name not in available_targets():
        print(f"unknown target {target_name!r}; available: {available_targets()}", file=sys.stderr)
        return 2

    target = load_target(target_name)
    try:
        dest = fetch_source(target)
    except Exception as exc:  # noqa: BLE001 — report network/git failures
        print(f"fetch-source {args.target} failed: {exc}", file=sys.stderr)
        return 1
    print(f"fetched {target.name} @ {target.source_commit} -> {dest}")
    return 0
