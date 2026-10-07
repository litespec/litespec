"""D71 ``DeriveStutterEncoding`` (Phase 3)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.loop_analysis import LoopAnalysis


def derive_stutter_encoding(loop: LoopAnalysis) -> Optional[dict]:
    """D71: derive the stutter encoding for a loop's variant.

    Returns ``None`` for ``iteration``-mode variants; a tagged union otherwise.
    """
    if loop.variant is None:
        return None
    mode = str(loop.variant.decreases_on)
    if mode == "iteration":
        return None
    return {"kind": "descent_through_alpha", "rank_witness_hash": "0" * 64}
