"""Abstraction layer records (§3, §9.15)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import AbstractionLayerId, DecreaseMode, FunctionTechnique
from litespec.schema.primitives import Identifier, SpecId, WitnessArtifact


class AbstractionRelation(LiteSpecModel):
    """§9.15 ``AbstractionRelation``."""

    name: Identifier
    source: str  # "LIR" | Identifier
    target: str  # "ISIR" | Identifier
    map_expr: str
    totality: bool
    notes: Optional[str] = None


class AbstractionLayer(LiteSpecModel):
    """§9.15 ``AbstractionLayer``."""

    id: AbstractionLayerId
    name: str
    derived: bool
    derivation: str
    soundness: str


class ISIRTarget(LiteSpecModel):
    """§9.15 ``ISIRTarget``."""

    isir_id: SpecId
    transition_ref: Identifier
    signal_scope: list[Identifier] = []


class RankWitness(LiteSpecModel):
    """§9.15 ``RankWitness``."""

    function: str
    decreases_on: DecreaseMode
    evidence: WitnessArtifact


class DialectStack(LiteSpecModel):
    """§9.15 ``DialectStack``."""

    dialects: list[str] = []
    passes: list[str] = []
    pipeline_ref: str


class AbstractionBlock(LiteSpecModel):
    """§3 ``AbstractionBlock``."""

    relation: AbstractionRelation
    layers: list[AbstractionLayerId] = []
    refinement_target: ISIRTarget
    rank_witness: Optional[RankWitness] = None
    dialect_stack: Optional[DialectStack] = None
    function_technique: Optional[FunctionTechnique] = None
