"""Refinement-chain recording (Phase 8)."""

from __future__ import annotations

from litespec.schema.refinement_chain import RefinementChain

#: Seam → refinement-chain link text.
SEAM_LINKS = {
    "c_to_lir": "T_C ⊑ T_LIR",
    "lir_to_unsafe": "T_LIR ⊑ T_Unsafe",
    "unsafe_to_safe": "T_Unsafe ⊑ T_Safe",
    "lir_to_isir": "T_LIR ⊑_α T_ISIR",
    "safe_to_isir": "T_Safe ⊑_α T_ISIR",
}


def record_chain(links: list[str]) -> RefinementChain:
    """Record a refinement chain as a ``RefinementChain`` record."""
    return RefinementChain(links=links)
