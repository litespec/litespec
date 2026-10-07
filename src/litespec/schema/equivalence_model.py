"""Differential equivalence layer records (§9.8, §9.13)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.decomposition_block import InterfacePropertyCheck, RecombinationRule
from litespec.schema.enums import (
    ContextGeneratorKind,
    ContextSplitKind,
    ContractSplitRule,
    DischargeStrategy,
    EquivalenceRelation,
    ProjectionSource,
    SealingMechanism,
)
from litespec.schema.extended_behavior import ExtendedBehaviorCheck
from litespec.schema.primitives import Identifier, LIRNodeRef, SpecId, WitnessArtifact
from litespec.schema.verification_layer import RefinementObligation


class ObservableProjection(LiteSpecModel):
    """§9.8 ``ObservableProjection``."""

    name: Identifier
    source: ProjectionSource
    description: str


class CommonFunctionality(LiteSpecModel):
    """§9.8 ``CommonFunctionality``."""

    name: Identifier
    abi_ref: str
    observable_projections: list[ObservableProjection] = []
    description: Optional[str] = None


class ExtendedFunctionality(LiteSpecModel):
    """§9.8 ``ExtendedFunctionality``."""

    name: Identifier
    abi_ref: Optional[str] = None
    native_contract: str
    rationale: str
    verification: str  # "native" | "out_of_scope"


class FunctionalSurface(LiteSpecModel):
    """§9.8 ``FunctionalSurface``."""

    name: Identifier
    common_functionality: list[CommonFunctionality] = []
    extended_functionality: Optional[list[ExtendedFunctionality]] = None
    notes: Optional[str] = None


class CoverageTarget(LiteSpecModel):
    """§9.13 ``CoverageTarget``."""

    operations_covered: float
    projection_depth: int
    boundary_cases: bool


class ContextGenerator(LiteSpecModel):
    """§9.13 ``ContextGenerator``."""

    kind: ContextGeneratorKind
    seed: int
    cardinality: Optional[int] = None
    coverage_target: CoverageTarget
    restricted_to: Identifier


class SealingModel(LiteSpecModel):
    """§9.13 ``SealingModel``."""

    mechanism: SealingMechanism
    reachable_without_extended: bool
    evidence: Optional[WitnessArtifact] = None


class DependencyAssumption(LiteSpecModel):
    """§9.14 ``DependencyAssumption``."""

    module_ref: SpecId
    observable_ref: Identifier
    behavior: EquivalenceRelation
    justification: str


class AssumptionSet(LiteSpecModel):
    """§9.14 ``AssumptionSet``."""

    dependencies: list[DependencyAssumption] = []
    invariants: list[str] = []


class Guarantee(LiteSpecModel):
    """§9.14 ``Guarantee``."""

    observable_ref: Identifier
    behavior: EquivalenceRelation
    evidence: WitnessArtifact


class GuaranteeSet(LiteSpecModel):
    """§9.14 ``GuaranteeSet``."""

    guarantees: list[Guarantee] = []


class Tolerance(LiteSpecModel):
    """§9.8 ``Tolerance``."""

    metric: str
    bound: str
    rationale: str


class ContextSubset(LiteSpecModel):
    """§9.8 ``ContextSubset``."""

    subset_of: Identifier
    filter_expr: Optional[str] = None
    notes: Optional[str] = None


class ContextSplitRule(LiteSpecModel):
    """§9.8 ``ContextSplitRule``."""

    kind: ContextSplitKind
    partition_of: Identifier
    evidence: Optional[WitnessArtifact] = None


class EquivalenceSubPart(LiteSpecModel):
    """§9.8 ``EquivalenceSubPart``."""

    name: Identifier
    lir_fragment: LIRNodeRef
    relation: EquivalenceRelation
    observable_ref: Identifier
    context_subset: ContextSubset
    refinement: Optional[RefinementObligation] = None


class EquivalenceDecomposition(LiteSpecModel):
    """§9.8 ``EquivalenceDecomposition``."""

    parent: Identifier
    sub_parts: list[EquivalenceSubPart] = []
    contract_split: ContractSplitRule
    recombination: RecombinationRule
    context_split: ContextSplitRule
    interface_checks: Optional[list[InterfacePropertyCheck]] = None


class EquivalenceModel(LiteSpecModel):
    """§9.8 ``EquivalenceModel``."""

    auto_inject: Optional[bool] = None
    relation: EquivalenceRelation
    common_surface: Optional[FunctionalSurface] = None
    context_generator: ContextGenerator
    sealing: SealingModel
    assumes: AssumptionSet
    guarantees: GuaranteeSet
    tolerance: Optional[Tolerance] = None
    strategy: DischargeStrategy
    checks: Optional[list[ExtendedBehaviorCheck]] = None
    decomposition: Optional[EquivalenceDecomposition] = None
    notes: Optional[str] = None
