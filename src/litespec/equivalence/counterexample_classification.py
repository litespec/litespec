"""Counterexample classification (Phase 8)."""

from __future__ import annotations

from litespec.equivalence.counterexample import Counterexample


def classify(ce: Counterexample) -> str:
    """Classify a counterexample by its originating seam kind."""
    return ce.kind
