"""Verus ``decreases`` synthesis from loop variants (Phase 5)."""

from __future__ import annotations

from litespec.schema.loop_analysis import LoopAnalysis


def synthesize_decreases(loops: list[LoopAnalysis]) -> list[str]:
    """Emit Verus ``decreases`` clauses from loop variants."""
    out: list[str] = []
    for loop in loops:
        if loop.variant is not None:
            out.append(f"decreases {loop.variant.expr}")
    return out
