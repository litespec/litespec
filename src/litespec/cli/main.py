"""LiteSpec command-line entry point.

``./run.sh <command>`` dispatches to ``python -m litespec <command>``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from litespec.cli.build_gn_command import build_gn_command
from litespec.cli.completeness_commands import ec_completeness_command, isir_completeness_command
from litespec.cli.conformance_command import conformance_command
from litespec.cli.coverage_command import coverage_command
from litespec.cli.decompose_command import decompose_command
from litespec.cli.emit_isir_command import emit_isir_command
from litespec.cli.extract_command import extract_command
from litespec.cli.fetch_source_command import fetch_source_command
from litespec.cli.generate_tests_command import generate_tests_command
from litespec.cli.lower_to_rust_command import lower_to_rust_command
from litespec.cli.pipeline_command import pipeline_command
from litespec.cli.repo_init_command import repo_init_command
from litespec.cli.validate_command import validate_command
from litespec.cli.verify_command import verify_command
from litespec.cli.verify_contracts_command import verify_contracts_command
from litespec.cli.verify_ec_command import verify_ec_command
from litespec.cli.verify_isir_command import verify_isir_command
from litespec.version import __version__

# Commands not yet implemented. They exist so ``run.sh`` can dispatch uniformly;
# each reports its target phase.
_STUB_COMMANDS: dict[str, str] = {
    "lift": "Phase 7 (InterScope trace lifting)",
    "check": "Phase 7 (InterScope property check)",
    "schema": "Phase 7 (ISIR schema validation)",
    "update-pin": "Phase 7 (InterScope pin update)",
}


def _pin_command() -> int:
    from litespec.interscope.config import interscope_commit

    sha = interscope_commit()
    if sha and sha != "unknown":
        print(sha)
        return 0
    print("unknown (run ./install.sh --interscope-only to record the local pin)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else argv
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("litespec " + __version__)
        print("usage: litespec <command> [options]")
        print("commands: validate, pin, conformance, " + ", ".join(sorted(_STUB_COMMANDS)))
        return 0

    command = argv[0]
    rest = argv[1:]

    if command == "validate":
        return validate_command(rest)
    if command == "decompose":
        return decompose_command(rest)
    if command == "extract":
        return extract_command(rest)
    if command == "emit-isir":
        return emit_isir_command(rest)
    if command == "fetch-source":
        return fetch_source_command(rest)
    if command in ("lower", "lower-to-rust"):
        return lower_to_rust_command(rest)
    if command == "pipeline":
        return pipeline_command(rest)
    if command == "verify":
        return verify_command(rest)
    if command == "verify-ec":
        return verify_ec_command(rest)
    if command == "verify-isir":
        return verify_isir_command(rest)
    if command == "verify-contracts":
        return verify_contracts_command(rest)
    if command == "pin":
        return _pin_command()
    if command == "conformance":
        return conformance_command(rest)
    if command == "coverage":
        return coverage_command(rest)
    if command == "generate-tests":
        return generate_tests_command(rest)
    if command == "build-gn":
        return build_gn_command(rest)
    if command == "repo-init":
        return repo_init_command(rest)
    if command == "isir-completeness":
        return isir_completeness_command(rest)
    if command == "ec-completeness":
        return ec_completeness_command(rest)
    if command in _STUB_COMMANDS:
        print(f"litespec {command}: not implemented ({_STUB_COMMANDS[command]}).", file=sys.stderr)
        return 2

    print(f"litespec: unknown command: {command}", file=sys.stderr)
    return 2
