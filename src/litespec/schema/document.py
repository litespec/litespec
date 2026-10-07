"""Document-level schema (§3, §4): ``LiteSpecDocument`` and friends."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import ConfigDict

from litespec.schema.abstraction_block import AbstractionBlock
from litespec.schema.base import LiteSpecModel
from litespec.schema.board_configuration import BoardConfiguration
from litespec.schema.configuration_layer import ConfigurationLayer
from litespec.schema.contract_layer import ContractLayer
from litespec.schema.decomposition_block import DecompositionBlock
from litespec.schema.enums import (
    BoundKind,
    BudgetPolicy,
    EnforcedAt,
    ExtendedBehaviorClass,
    ModulePhase,
    ModuleType,
    PropertyKind,
    RecordPhase,
    SpecCategory,
    SpecPriority,
    VerifyTool,
)
from litespec.schema.equivalence_model import EquivalenceModel
from litespec.schema.extended_behavior import ExtendedBehaviorModel
from litespec.schema.global_property_block import GlobalPropertyBlock
from litespec.schema.hardware import HardwareEncodingLayer
from litespec.schema.ipc import IPCLayer
from litespec.schema.loop_analysis import LoopAnalysis
from litespec.schema.lowering_metadata import LoweringMetadata
from litespec.schema.primitives import HashBindingsBlock, Identifier, SemVer, SpecId
from litespec.schema.service_interface import ServiceDependency, ServiceInterface
from litespec.schema.source_layer import SourceLayer
from litespec.schema.state_machine_layer import StateMachineLayer
from litespec.schema.syscall_mapping import SyscallMapping
from litespec.schema.verification_layer import VerificationLayer


class ProfileRef(LiteSpecModel):
    """§3 ``ProfileRef ::= { name, version }``."""

    name: Identifier
    version: SemVer


class SizeBudget(LiteSpecModel):
    """§3 ``SizeBudget``."""

    max_bytes: int
    rationale: Optional[str] = None
    enforced_at: EnforcedAt


class DependencyBudget(LiteSpecModel):
    """§3 ``DependencyBudget``."""

    max_count: int
    rationale: Optional[str] = None
    enforced_at: EnforcedAt


class ModuleHeader(LiteSpecModel):
    """§3/§4.4 ``ModuleHeader``."""

    name: Identifier
    display_name: str
    phase: ModulePhase
    module_type: ModuleType
    source_repo: str
    source_commit: str
    extraction_timestamp: str
    extractor: str
    size_budget: Optional[SizeBudget] = None
    dependency_budget: Optional[DependencyBudget] = None
    can_exclude: Optional[bool] = None
    service_dependencies: Optional[list[ServiceDependency]] = None


class SpecRecord(LiteSpecModel):
    """§3 ``SpecRecord``.

    Note (Phase 0): ``lowering`` and ``verification`` are mandatory in §3, but the
    §18.1 worked example omits them; they are therefore modeled optional here.
    """

    id: SpecId
    title: str
    category: SpecCategory
    priority: SpecPriority
    record_phase: Optional[RecordPhase] = None
    source: SourceLayer
    contract: ContractLayer
    state_machine: Optional[StateMachineLayer] = None
    hardware_encoding: Optional[HardwareEncodingLayer] = None
    ipc: Optional[IPCLayer] = None
    service_interface: Optional[ServiceInterface] = None
    syscall_mapping: Optional[list[SyscallMapping]] = None
    configuration: Optional[ConfigurationLayer] = None
    equivalence: Optional[EquivalenceModel] = None
    extended_behavior: Optional[ExtendedBehaviorModel] = None
    abstraction: Optional[AbstractionBlock] = None
    decomposition: Optional[DecompositionBlock] = None
    global_props: Optional[GlobalPropertyBlock] = None
    loop_analysis: Optional[list[LoopAnalysis]] = None
    lowering: Optional[LoweringMetadata] = None
    verification: Optional[VerificationLayer] = None
    depends_on: Optional[list[SpecId]] = None


class BoundingMetadata(LiteSpecModel):
    """§4.6 ``BoundingMetadata``."""

    bound: Optional[int] = None
    bound_kind: BoundKind
    timeout: Optional[str] = None
    budget_policy: BudgetPolicy


class LLMPolicy(LiteSpecModel):
    """§4.6 ``LLMPolicy``."""

    allow_llm_generated: bool
    require_validation: bool
    approved_tools: list[str] = []
    require_provenance: bool


class ProfileValidation(LiteSpecModel):
    """§4.6 ``ProfileValidation``."""

    preserved_properties: list[PropertyKind] = []
    excluded_properties: list[PropertyKind] = []
    verification_targets: list[VerifyTool] = []
    coverage_threshold: int
    bounding_metadata: Optional[dict[str, BoundingMetadata]] = None
    llm_policy: Optional[LLMPolicy] = None


class VerificationBudget(LiteSpecModel):
    """§4.6 ``VerificationBudget``."""

    max_checks: int
    max_discharge_time: str
    priority_classes: list[ExtendedBehaviorClass] = []
    budget_policy: BudgetPolicy


class BuildProfile(LiteSpecModel):
    """§4.6 ``BuildProfile``."""

    name: Identifier
    included_modules: list[Identifier] = []
    excluded_modules: list[Identifier] = []
    max_kernel_size: int
    config_preset: Optional[Identifier] = None
    config_overrides: Optional[dict[Identifier, Any]] = None
    board: Optional[Identifier] = None
    verification_budget: Optional[VerificationBudget] = None
    validation: ProfileValidation


class LLMProvenanceRecord(LiteSpecModel):
    """§17.11 ``LLMProvenanceRecord`` (permissive placeholder in Phase 0)."""

    model_config = ConfigDict(extra="allow")

    tool: Optional[str] = None
    model: Optional[str] = None
    prompt_hash: Optional[str] = None
    timestamp: Optional[str] = None


class LiteSpecDocument(LiteSpecModel):
    """§3 ``LiteSpecDocument``.

    ``lir_specs`` and ``hash_bindings`` are top-level keys used by the §18.1
    worked example (LIRSpec list and HashBindingsBlock respectively).
    """

    litespec_version: SemVer
    profile: ProfileRef
    module: ModuleHeader
    specs: list[SpecRecord] = []
    build_profiles: Optional[list[BuildProfile]] = None
    board_configuration: Optional[BoardConfiguration] = None
    llm_provenance: Optional[list[LLMProvenanceRecord]] = None
    lir_specs: Optional[list[Any]] = None
    hash_bindings: Optional[HashBindingsBlock] = None
