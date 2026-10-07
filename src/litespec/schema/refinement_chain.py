"""Refinement-chain record (Phase 8 placeholder)."""

from __future__ import annotations

from typing import Optional

from pydantic import ConfigDict

from litespec.schema.base import LiteSpecModel


class RefinementChain(LiteSpecModel):
    """Refinement-chain record (T_C ⊑ T_LIR ⊑ T_Unsafe ⊑ T_Safe ⊑_α T_ISIR)."""

    model_config = ConfigDict(extra="allow")

    links: list[str] = []
    notes: Optional[str] = None
