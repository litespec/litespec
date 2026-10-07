"""Seam Unsafe↔Safe equivalence (Track 1)."""

from __future__ import annotations

from litespec.equivalence.proof_system import check_seam
from litespec.pipeline.pipeline_state import CheckResult

SEAM = "unsafe_to_safe"
RELATION = "observational"


def check(unsafe: object | None = None, safe: object | None = None) -> CheckResult:
    return check_seam(SEAM, RELATION, (unsafe, safe))
