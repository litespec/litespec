"""Target profile schema (§12)."""

from __future__ import annotations

from typing import Any, Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.primitives import Identifier, SemVer


class ABIReference(LiteSpecModel):
    """§12 ``ABIReference ::= { repo, commit, file, hash }``."""

    repo: str
    commit: str
    file: str
    hash: str


class TargetProfile(LiteSpecModel):
    """§12 ``TargetProfile``."""

    name: Identifier
    version: SemVer
    inherits: Optional[Identifier] = None
    supported_phases: list[str] = []
    supported_modules: list[Identifier] = []
    baseline_abi: Optional[ABIReference] = None
    target_architectures: list[str] = []
    target_specific: Optional[dict[str, Any]] = None
    profile_gates_ack: Optional[list[int]] = None
