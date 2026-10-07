"""EC completeness check (Phase 9)."""

from __future__ import annotations

from litespec.equivalence.layered_ec import run_layered_ec
from litespec.pipeline.pipeline_state import CheckResult


def check_ec_completeness(**artifacts) -> CheckResult:
    """All five seam obligations must discharge (pass artifacts to run the checks)."""
    result, _chain = run_layered_ec(**artifacts)
    return result
