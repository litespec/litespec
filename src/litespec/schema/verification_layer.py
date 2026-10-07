"""Verification layer schema (§9.2)."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import (
    CapabilityKind,
    ObligationKind,
    PropertyKind,
    VerificationStatus,
    VerifyLevel,
    VerifyTool,
)
from litespec.schema.primitives import Identifier, WitnessArtifact


class CapabilityContractRef(LiteSpecModel):
    """§9.6 ``CapabilityContractRef``."""

    name: Identifier
    kind: CapabilityKind
    contract_expr: str
    description: str
    evidence: Optional[WitnessArtifact] = None


class VerifyTarget(LiteSpecModel):
    """§9.2 ``VerifyTarget``."""

    tool: VerifyTool
    level: VerifyLevel
    description: str
    capabilities: Optional[list[CapabilityContractRef]] = None
    verification_status: VerificationStatus


class Property(LiteSpecModel):
    """§9.2 ``Property ::= { property, expression, scope? }``."""

    property: PropertyKind
    expression: str
    scope: Optional[str] = None


class RefinementObligation(LiteSpecModel):
    """§9.2 ``RefinementObligation``."""

    id: str
    from_: str = Field(alias="from")
    to: str
    tool: str
    obligation: str
    discharge_strategy: str
    abstraction_ref: Optional[str] = None
    decomposition_ref: Optional[str] = None


class ProofObligation(LiteSpecModel):
    """§9.2 ``ProofObligation``."""

    id: Identifier
    obligation_kind: ObligationKind
    statement: str
    path_dag_ref: Optional[Identifier] = None
    backend: VerifyTool
    tactic_hints: Optional[list[str]] = None


class VerificationLayer(LiteSpecModel):
    """§9.2 ``VerificationLayer``."""

    targets: list[VerifyTarget] = []
    properties: list[Property] = []
    refinement: list[RefinementObligation] = []
    proof_obligations: Optional[list[ProofObligation]] = None
