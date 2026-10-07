"""Rust-layer record (Phase 4 placeholder; modeled permissively)."""

from __future__ import annotations

from typing import Optional

from pydantic import ConfigDict

from litespec.schema.base import LiteSpecModel
from litespec.schema.primitives import Identifier


class RustLayer(LiteSpecModel):
    """§17/Rust-layer record. Phase 4 placeholder."""

    model_config = ConfigDict(extra="allow")

    name: Optional[Identifier] = None
    kind: Optional[str] = None
