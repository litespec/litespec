"""Equivalence-relation lattice (§9.8.1)."""

from __future__ import annotations

#: The pre-order ``exact ⊑ bisimulation ⊑ weak_bisimulation ⊑ observational ⊑ refinement_only``.
RELATION_LATTICE = ("exact", "bisimulation", "weak_bisimulation", "observational", "refinement_only")


def stronger_or_equal(a: str, b: str) -> bool:
    """``a ⊑ b`` iff ``a`` is at least as strong as ``b``."""
    return RELATION_LATTICE.index(a) <= RELATION_LATTICE.index(b)


def discharge(a: str, b: str) -> bool:
    """A guarantee ``a`` discharges an obligation ``b`` iff ``a ⊑ b`` (Rule AH-3b)."""
    return stronger_or_equal(a, b)
