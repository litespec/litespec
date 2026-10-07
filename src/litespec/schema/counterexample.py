"""Counterexample record (Phase 6/8 placeholder)."""

from __future__ import annotations

from typing import Optional

from pydantic import ConfigDict

from litespec.schema.base import LiteSpecModel


class Counterexample(LiteSpecModel):
    """A counterexample trace. Phase 6/8 placeholder."""

    model_config = ConfigDict(extra="allow")

    kind: Optional[str] = None
    description: Optional[str] = None
