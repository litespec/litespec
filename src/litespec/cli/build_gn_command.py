"""``build-gn`` command: generate the target's OpenHarmony ``BUILD.gn``."""

from __future__ import annotations

import argparse
import sys

from litespec.build import generate_build_gn
from litespec.targets import available_targets, load_target, resolve_target


def build_gn_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="litespec build-gn", description="Generate the target's BUILD.gn")
    parser.add_argument("target", nargs="?", default=None, help="target name (config/targets/<name>.yaml)")
    args = parser.parse_args(argv)

    target_name = resolve_target(args.target)
    if target_name not in available_targets():
        print(f"unknown target {target_name!r}; available: {available_targets()}", file=sys.stderr)
        return 2

    target = load_target(target_name)
    print(generate_build_gn(target), end="")
    return 0
