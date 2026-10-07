"""The LIR→ISIR refinement relation ``⊑_α`` (Definition 14.19.2)."""

from __future__ import annotations


def defines_refinement(source: str, target: str) -> bool:
    """Whether a refinement ``source ⊑_α target`` is declared.

    ``⊑_α`` holds iff ``∀σ, σ'. σ →_LIR σ' ⟹ α(σ) →*_ISIR α(σ')`` (Theorem 14.85x,
    proof status: stated). Concrete discharge is delegated to InterScope (Phase 7).
    """
    return source == "LIR" and target == "ISIR"


def refinement_chain(*links: str) -> list[str]:
    """Record a refinement chain (T_C ⊑ T_LIR ⊑ T_Unsafe ⊑ T_Safe ⊑_α T_ISIR)."""
    return list(links)
