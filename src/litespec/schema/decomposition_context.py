"""Decomposition context records (§9.18)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.decomposition_block import PropertyLattice
from litespec.schema.enums import (
    AbstractionLayerId,
    ContractSplitRule,
    DecompositionStage,
    FunctionTechnique,
    GluingSeedSource,
)
from litespec.schema.equivalence_model import ContextSplitRule
from litespec.schema.exit_state import ProvenanceMap
from litespec.schema.fragment_complexity import FragmentComplexity
from litespec.schema.loop_analysis import LoopAnalysis
from litespec.schema.primitives import Identifier, LabelPath, LIRNodeRef, PropertyRef, SpecId


class SpecRecordRef(LiteSpecModel):
    """§9.18 ``SpecRecordRef ::= { id }``."""

    id: SpecId


class ContextualSubPart(LiteSpecModel):
    """§9.18 ``ContextualSubPart``."""

    name: Identifier
    lir_fragment: LIRNodeRef
    properties: list[PropertyRef] = []
    injected_checks: list[str] = []
    equivalence_obligs: list[object] = []
    required_layers: list[AbstractionLayerId] = []
    technique: FunctionTechnique


class InjectionProjection(LiteSpecModel):
    """§9.18 ``InjectionProjection``."""

    sub_part_map: dict[Identifier, list[str]] = {}
    parent_level: list[str] = []
    unassigned: list[str] = []


class EquivalenceSplit(LiteSpecModel):
    """§9.18 ``EquivalenceSplit``."""

    parent_contract: Identifier
    sub_contracts: list[str] = []
    contract_split: ContractSplitRule
    context_split: ContextSplitRule


class GluingSeed(LiteSpecModel):
    """§9.18 ``GluingSeed``."""

    name: Identifier
    scope: list[SpecId] = []
    expr: str
    source: GluingSeedSource


class LoopContext(LiteSpecModel):
    """§9.18 ``LoopContext``."""

    loops: list[LoopAnalysis] = []
    optimized: bool
    optimization_report: Optional[str] = None


class ExitStateContext(LiteSpecModel):
    """§9.18 ``ExitStateContext``."""

    enabled: bool
    return_targets: list[LabelPath] = []
    break_targets: list[LabelPath] = []
    continue_targets: list[LabelPath] = []
    provenance_map: Optional[ProvenanceMap] = None


class DecompositionContext(LiteSpecModel):
    """§9.18 ``DecompositionContext``."""

    spec_id: SpecId
    parent: SpecRecordRef
    should_decompose: bool
    sub_parts: list[ContextualSubPart] = []
    property_lattice: PropertyLattice
    injected_projection: InjectionProjection
    equivalence_split: Optional[EquivalenceSplit] = None
    gluing_seeds: list[GluingSeed] = []
    loop_context: Optional[LoopContext] = None
    exit_state_context: Optional[ExitStateContext] = None
    stage: DecompositionStage
    hash: str
    fragment_complexity: Optional[FragmentComplexity] = None
