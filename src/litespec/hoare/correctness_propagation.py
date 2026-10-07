"""Correctness-kind propagation (§9.21.4 ``effective_correctness``)."""

from __future__ import annotations


def correctness_of_rule(rule: str, child_correctness: list[str]) -> str:
    """Bottom-up correctness for a fragment with the given rule."""
    if rule in ("assign", "skip", "return"):
        return "total"
    if rule == "call":
        return "partial"  # callee contract totalness is not asserted in Phase 1
    if rule in ("seq", "if", "let", "while", "consequence", "quant_forall", "quant_exists_finite"):
        if child_correctness and all(c == "total" for c in child_correctness):
            return "total"
    return "partial"
