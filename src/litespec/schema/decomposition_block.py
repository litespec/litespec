"""Property decomposition layer records (§9.16, §3)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import (
    AbstractionLayerId,
    CorrectnessKind,
    FunctionTechnique,
    HoareRuleKind,
    InterfaceRelationKind,
    PropertyKind,
    RecombinationKind,
    SubPartKind,
)
from litespec.schema.exit_state import ExitStateModel
from litespec.schema.fragment_complexity import FragmentComplexity
from litespec.schema.hoare_triple import HoareTriple, ParentHoareTriple
from litespec.schema.path_condition_dag import PathConditionDAG, PathDagOp
from litespec.schema.primitives import Identifier, LIRNodeRef, Predicate, PropertyRef, WitnessArtifact
from litespec.schema.verification_layer import RefinementObligation


class PropertyLattice(LiteSpecModel):
    """§9.16 ``PropertyLattice ::= { order, notes? }``."""

    order: list[list[str]] = []
    notes: Optional[str] = None


class NestedSharedPost(LiteSpecModel):
    """§9.16 ``NestedSharedPost``."""

    branches: list[Identifier] = []
    recursive_post: Predicate
    evidence: WitnessArtifact


class InterfacePropertyCheck(LiteSpecModel):
    """§9.16 ``InterfacePropertyCheck``."""

    id: Identifier
    caller: Identifier
    callee: Identifier
    relation_kind: InterfaceRelationKind
    required: list[PropertyKind] = []
    provided: list[PropertyKind] = []
    evidence: WitnessArtifact
    intermediate_assertion: Optional[Predicate] = None
    shared_post: Optional[Predicate] = None
    nested_shared_post: Optional[NestedSharedPost] = None


class RecombinationRule(LiteSpecModel):
    """§9.8 ``RecombinationRule``."""

    kind: RecombinationKind
    hoare_rule: Optional[HoareRuleKind] = None
    glue_expr: Optional[str] = None
    evidence: Optional[WitnessArtifact] = None


class SubPart(LiteSpecModel):
    """§9.16 ``SubPart``."""

    name: Identifier
    lir_fragment: LIRNodeRef
    kind: SubPartKind
    properties: list[PropertyRef] = []
    technique: FunctionTechnique
    required_layers: list[AbstractionLayerId] = []
    refinement: Optional[RefinementObligation] = None
    hoare_triple: Optional[HoareTriple] = None


class DecompositionBlock(LiteSpecModel):
    """§9.16 ``DecompositionBlock``."""

    should_decompose: bool
    parent_triple: Optional[ParentHoareTriple] = None
    sub_parts: list[SubPart] = []
    property_lattice: PropertyLattice
    interface_checks: list[InterfacePropertyCheck] = []
    recombination: Optional[RecombinationRule] = None
    exit_state_model: Optional[ExitStateModel] = None
    path_dag: Optional[PathConditionDAG] = None
    path_dag_op: Optional[PathDagOp] = None
    effective_correctness: Optional[CorrectnessKind] = None
    fragment_complexity: Optional[FragmentComplexity] = None
