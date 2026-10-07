"""Lowering metadata schema (§9.1)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import (
    AssertionFormat,
    ChannelImpl,
    ContextPolicy,
    DagSerialization,
    DoorbellImpl,
    ExitStatePolicy,
    LlmTool,
    LoopOptPolicy,
    PrimaryTool,
    PromotionPolicy,
    RecombinationPolicy,
    RefinementStrategy,
    ReproStrategy,
    RestartBackoff,
    RustStrategy,
    SaturationPolicy,
    SeqCompositionPolicy,
    SupervisorImpl,
    SyncImpl,
    UnsafePolicy,
)
from litespec.schema.primitives import Bound


class RustLowering(LiteSpecModel):
    strategy: RustStrategy
    strategy_params: Optional[dict[str, str]] = None
    target_file: str
    function_name: str
    verus_annotations: bool
    unsafe_policy: UnsafePolicy
    llm_model: Optional[str] = None
    llm_seed: Optional[int] = None
    llm_prompt_hash: Optional[str] = None


class ISIRLowering(LiteSpecModel):
    type_encoding_ref: str
    assertion_format: AssertionFormat
    signal_prefix: str
    capability_ref: Optional[str] = None


class TLALowering(LiteSpecModel):
    module_name: str
    fairness: Optional[str] = None
    symmetry: Optional[list[str]] = None


class IPCLowering(LiteSpecModel):
    channel_impl: ChannelImpl
    doorbell_impl: DoorbellImpl
    sync_impl: SyncImpl


class ServiceLowering(LiteSpecModel):
    supervisor_impl: SupervisorImpl
    restart_backoff: RestartBackoff


class TraceLiftLowering(LiteSpecModel):
    default_bound: Bound
    max_bound: Bound
    saturation_policy: SaturationPolicy


class ReproducibilityLowering(LiteSpecModel):
    seed: int
    tool_version: str
    strategy: ReproStrategy


class AbstractionLowering(LiteSpecModel):
    dialect_stack: list[str] = []
    lowering_pipeline: list[str] = []
    refinement_strategy: RefinementStrategy
    rank_witness_ref: Optional[str] = None


class RustVerificationLowering(LiteSpecModel):
    primary_tool: PrimaryTool
    fallback_tool: Optional[str] = None
    llm_assisted: bool
    llm_tool: LlmTool
    bound: Optional[int] = None
    timeout: Optional[str] = None


class DecompositionLowering(LiteSpecModel):
    context_policy: ContextPolicy
    context_hash: Optional[str] = None
    pipeline_stage: list[str] = []


class LoopOptimizationLowering(LiteSpecModel):
    policy: LoopOptPolicy
    max_unroll: Optional[int] = None
    traceability_hash: Optional[str] = None


class PromotionThreshold(LiteSpecModel):
    max_dag_nodes: Optional[int] = None
    max_dag_branching: Optional[int] = None


class HoareLowering(LiteSpecModel):
    enabled: bool
    recombination_policy: RecombinationPolicy
    rule_coverage_hash: Optional[str] = None
    exit_state_policy: ExitStatePolicy
    seq_composition_policy: SeqCompositionPolicy
    promotion_policy: PromotionPolicy
    promotion_threshold: Optional[PromotionThreshold] = None


class PathConditionLowering(LiteSpecModel):
    representation: str = "dag"
    dag_serialization: DagSerialization
    external_format: Optional[str] = None


class LoweringMetadata(LiteSpecModel):
    """§9.1 ``LoweringMetadata`` (all sub-fields mandatory per Rule 9.2b)."""

    rust: RustLowering
    isir: ISIRLowering
    tla: TLALowering
    ipc: IPCLowering
    service: ServiceLowering
    trace_lift: TraceLiftLowering
    reproducibility: ReproducibilityLowering
    abstraction: AbstractionLowering
    rust_verification: RustVerificationLowering
    decomposition: DecompositionLowering
    loop_optimization: LoopOptimizationLowering
    hoare: HoareLowering
    path_condition: PathConditionLowering
