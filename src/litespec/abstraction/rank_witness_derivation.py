"""D45 ``DeriveRankWitness`` (Phase 3)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.abstraction_block import RankWitness
from litespec.schema.loop_analysis import LoopAnalysis
from litespec.schema.primitives import WitnessArtifact


def requires_rank(loops: list[LoopAnalysis]) -> bool:
    """D45 ``requires_rank``: recursion or a bounded loop."""
    return bool(loops) and any(str(l.loop_kind) == "recursion" or l.bound is not None for l in loops)


def _evidence() -> WitnessArtifact:
    return WitnessArtifact(kind="proof", uri="evidence/rank_witness.json", hash="0" * 64)


def derive_rank_witness(loops: list[LoopAnalysis]) -> Optional[RankWitness]:
    """D45: derive a ``RankWitness`` when ``requires_rank`` holds.

    Uses the first loop's ``variant`` when present, else a synthesized
    ``remaining_iterations`` measure.
    """
    if not requires_rank(loops):
        return None
    for loop in loops:
        if loop.variant is not None:
            return RankWitness(
                function=loop.variant.expr,
                decreases_on=str(loop.variant.decreases_on),
                evidence=loop.variant.evidence or _evidence(),
            )
    return RankWitness(
        function="lambda sigma. remaining_iterations(sigma)",
        decreases_on="iteration",
        evidence=_evidence(),
    )
