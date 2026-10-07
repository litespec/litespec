"""Kani unwind-bound derivation (Phase 5)."""

from __future__ import annotations

from litespec.schema.loop_analysis import LoopAnalysis


def derive_unwind_bound(loops: list[LoopAnalysis]) -> int:
    """Derive the Kani unwind bound from the first bounded loop (default 1)."""
    for loop in loops:
        if loop.bound is not None:
            return loop.bound.bound
    return 1
