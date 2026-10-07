"""Seam C↔LIR equivalence (Track 1)."""

from __future__ import annotations

from litespec.equivalence.proof_system import check_seam
from litespec.pipeline.pipeline_state import CheckResult

SEAM = "c_to_lir"
RELATION = "observational"


def check(c_source: object | None = None, lir: object | None = None) -> CheckResult:
    return check_seam(SEAM, RELATION, (c_source, lir))
