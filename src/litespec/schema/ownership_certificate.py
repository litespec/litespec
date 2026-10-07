"""Ownership-certificate record (Phase 4 placeholder)."""

from __future__ import annotations

from typing import Optional

from pydantic import ConfigDict

from litespec.schema.base import LiteSpecModel
from litespec.schema.primitives import Identifier, WitnessArtifact


class OwnershipCertificate(LiteSpecModel):
    """Ownership-certificate record. Phase 4 placeholder."""

    model_config = ConfigDict(extra="allow")

    subject: Optional[Identifier] = None
    evidence: Optional[WitnessArtifact] = None
