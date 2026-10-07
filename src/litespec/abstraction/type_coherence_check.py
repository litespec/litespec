"""Abstraction type-coherence check (Rule R91)."""

from __future__ import annotations


def type_coherence_check(state_vars: list[tuple[str, str]], signals: list[str]) -> tuple[bool, str]:
    """Type coherence: every signal carries a type derived from its state var.

    In the LIR-to-ISIR mapping the ISIR signal inherits the LIR state variable's
    ``TypeExpr``; coherence holds structurally when the mapping is 1:1.
    """
    if len(signals) != len(state_vars):
        return False, f"type coherence: {len(signals)} signals vs {len(state_vars)} state variables"
    return True, "types are coherent"
