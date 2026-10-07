"""``isir-completeness`` / ``ec-completeness`` commands (Phase 9)."""

from __future__ import annotations

import argparse
from pathlib import Path

from litespec.equivalence import verify_function
from litespec.targets import isir_output_dir, load_target, resolve_target
from litespec.type_mapping import load_type_model
from litespec.validation import check_isir_completeness


def isir_completeness_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="litespec isir-completeness", description="Check ISIR completeness (Phase 9)")
    parser.add_argument("--target", default=None)
    parser.add_argument("--module", default=None, help="restrict to one module (e.g. kernel_mm)")
    args = parser.parse_args(argv)

    target = load_target(resolve_target(args.target))
    modules = target.modules
    if args.module:
        if args.module not in modules:
            print(f"isir-completeness: unknown module {args.module!r} (have {sorted(modules)})", file=__import__("sys").stderr)
            return 2
        modules = {args.module: modules[args.module]}

    result = check_isir_completeness(modules, isir_output_dir(target))
    scope = f" (module: {args.module})" if args.module else ""
    print(f"isir-completeness [{target.name}]{scope}: {result.status}")
    for report in result.reports:
        print("  " + report)
    for error in result.errors:
        print("  " + error)
    return 0 if result.ok else 1


def ec_completeness_command(argv: list[str]) -> int:
    """Check every in-scope function discharges its five EC seams (Phase 9)."""
    parser = argparse.ArgumentParser(prog="litespec ec-completeness", description="Check EC completeness (Phase 9)")
    parser.add_argument("--target", default=None)
    parser.add_argument("--module", default=None, help="restrict to one module (e.g. kernel_mm)")
    parser.add_argument("--source", required=True, help="combined .c source file")
    args = parser.parse_args(argv)

    target = load_target(resolve_target(args.target))
    modules = target.modules
    if args.module:
        if args.module not in modules:
            print(f"ec-completeness: unknown module {args.module!r} (have {sorted(modules)})", file=__import__("sys").stderr)
            return 2
        modules = {args.module: modules[args.module]}

    tm = load_type_model(target.type_model)
    src = Path(args.source).read_bytes()

    passed = failed = 0
    for module, fns in modules.items():
        for name in fns:
            result, chain = verify_function(src, name, type_model=tm)
            if result.status == "pass":
                passed += 1
            else:
                failed += 1
            print(f"ec-completeness [{module}/{name}]: {result.status} ({len(chain.links)} seams)")
            for r in result.reports:
                print(f"      {r}")
            for e in result.errors:
                print(f"      error: {e}")
            for w in result.warnings:
                print(f"      warn: {w}")

    print(f"ec-completeness: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1
