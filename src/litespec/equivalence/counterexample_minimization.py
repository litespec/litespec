"""Counterexample minimization (Phase 8)."""

from __future__ import annotations

from litespec.equivalence.counterexample import Counterexample


def minimize(ce: Counterexample) -> Counterexample:
    """Minimize a counterexample trace (identity in Phase 8; refinement follows)."""
    return ce
