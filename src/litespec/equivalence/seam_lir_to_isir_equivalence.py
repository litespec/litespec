"""Seam LIR↔ISIR equivalence via α (Track 2)."""

from __future__ import annotations

from litespec.equivalence.proof_system import check_seam
from litespec.pipeline.pipeline_state import CheckResult

SEAM = "lir_to_isir"
RELATION = "refinement_only"


def check(lir: object | None = None, isir: object | None = None) -> CheckResult:
    return check_seam(SEAM, RELATION, (lir, isir))
