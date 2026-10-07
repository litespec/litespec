"""Seam LIR↔Unsafe equivalence (Track 1)."""

from __future__ import annotations

from litespec.equivalence.proof_system import check_seam
from litespec.pipeline.pipeline_state import CheckResult

SEAM = "lir_to_unsafe"
RELATION = "bisimulation"


def check(lir: object | None = None, rust: object | None = None, c_source: object | None = None) -> CheckResult:
    return check_seam(SEAM, RELATION, (lir, rust, c_source))
