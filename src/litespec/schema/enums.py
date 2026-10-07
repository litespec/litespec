"""Shared enumerations for the LiteSpec wire format (Volume 1 §3–§12).

Every enum value equals its member name. Pydantic coerces YAML strings into these
members on load; ``model_dump(mode="json")`` emits plain strings on dump.
"""

from __future__ import annotations

import enum
from typing import Literal

# --------------------------------------------------------------------------- #
# factory
# --------------------------------------------------------------------------- #


def _enum(name: str, *members: str) -> type[enum.Enum]:
    return enum.StrEnum(name, {m: m for m in members})  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# §3–§4
# --------------------------------------------------------------------------- #

ModulePhase = _enum("ModulePhase", "lightweight", "extended", "standard")
ModuleType = _enum("ModuleType", "kernel", "user_space_service", "library")
SpecCategory = _enum("SpecCategory", "requirement", "invariant")
SpecPriority = _enum("SpecPriority", "critical", "high", "medium", "low")
RecordPhase = _enum("RecordPhase", "phase_1", "phase_2", "phase_3")
CorrectnessKind = _enum("CorrectnessKind", "total", "partial", "mixed")
DecreaseMode = _enum("DecreaseMode", "iteration", "stutter", "both")
ControlFlow = _enum("ControlFlow", "normal", "returning", "breaking", "continuing")
PathNodeKind = _enum(
    "PathNodeKind",
    "entry",
    "seq",
    "branch_then",
    "branch_else",
    "loop_body",
    "loop_exit",
    "return",
    "break",
    "continue",
)
ExitTargetKind = _enum("ExitTargetKind", "return", "break", "continue")
EnforcedAt = _enum("EnforcedAt", "compile_time", "runtime", "both")
BudgetPolicy = _enum("BudgetPolicy", "warn", "strict")
BoundKind = _enum("BoundKind", "cycles", "steps", "states", "depth", "none", "unbounded")

# --------------------------------------------------------------------------- #
# §6 contract
# --------------------------------------------------------------------------- #

VerificationMethod = _enum(
    "VerificationMethod",
    "manual_review",
    "static_analysis",
    "runtime_profiling",
    "isir_itp",
    "verus",
    "kani",
    "smack",
    "rem",
    "symbiyosys",
)
BoundType = _enum("BoundType", "worst_case", "average", "percentile")
RegisterRole = _enum("RegisterRole", "input", "output", "clobbered", "preserved")
FenceKind = _enum("FenceKind", "acquire", "release", "full", "compiler")
FenceScope = _enum("FenceScope", "single_core", "multi_core", "device")
PriorityProtocol = _enum("PriorityProtocol", "basic", "immediate_ceiling", "original_ceiling")
WcetMethod = _enum("WcetMethod", "abstract_interpretation", "measurement_based", "hybrid")
CacheModel = _enum("CacheModel", "none", "always_hit", "always_miss", "precise")
PipelineModel = _enum("PipelineModel", "none", "in_order", "out_of_order")

# --------------------------------------------------------------------------- #
# §7 state machine
# --------------------------------------------------------------------------- #

ActionContext = _enum("ActionContext", "thread", "isr", "both")

# --------------------------------------------------------------------------- #
# §8 hardware encoding
# --------------------------------------------------------------------------- #

TimingKind = _enum("TimingKind", "bounded_latency", "unbounded", "invariant")
AssertionFormat = _enum("AssertionFormat", "LTL", "SVA", "PSL")
OverflowBehavior = _enum("OverflowBehavior", "none", "assert", "saturate")
EncodingStrategy = _enum("EncodingStrategy", "bounded", "symbolic", "approximated")

# --------------------------------------------------------------------------- #
# §9 layers
# --------------------------------------------------------------------------- #

VerifyLevel = _enum("VerifyLevel", "primary", "bounded", "model_check", "supplementary")
VerificationStatus = _enum("VerificationStatus", "verified", "approximate")

VerifyTool = _enum(
    "VerifyTool",
    "verus",
    "kani",
    "tlc",
    "isir_itp",
    "cargo-test",
    "differential_test",
    "differential_equivalence_checker",
    "ipc_protocol_checker",
    "stack_usage_analyzer",
    "wcet_analyzer",
    "size_analyzer",
    "exclusion_checker",
    "service_dependency_checker",
    "service_isolation_checker",
    "syscall_compatibility_checker",
    "ilang",
    "smt_refinement_checker",
    "smack",
    "creusot",
    "prusti",
    "rem",
    "charon",
    "aeneas",
    "koika",
    "acl2",
    "symbiyosys",
    "verilator",
)

PropertyKind = _enum(
    "PropertyKind",
    "safety",
    "liveness",
    "termination",
    "memory_safety",
    "performance",
    "abi_compatibility",
    "ipc_correctness",
    "gpu_command_correctness",
    "context_safety",
    "exclusion_safety",
    "graceful_degradation",
    "service_isolation",
    "service_dependency_safety",
    "syscall_compatibility",
    "differential_equivalence",
    "lir_isir_refinement",
    "resource_bound",
    "deadlock_freedom",
    "throughput",
)

ObligationKind = _enum(
    "ObligationKind",
    "hoare_seq",
    "hoare_if",
    "hoare_while",
    "hoare_return",
    "refinement",
    "invariant",
    "termination",
)

ChannelKind = _enum("ChannelKind", "ring_buffer", "message_queue", "shared_memory")
ChannelOrdering = _enum("ChannelOrdering", "fifo", "priority", "unordered")
OverflowPolicy = _enum("OverflowPolicy", "block", "drop", "overwrite")
DoorbellMechanism = _enum("DoorbellMechanism", "mmio", "mailbox", "interrupt")
SyncKind = _enum("SyncKind", "atomic", "futex", "semaphore", "spinlock")
SupervisorImpl = _enum("SupervisorImpl", "task", "thread", "process")
RestartPolicy = _enum("RestartPolicy", "always", "on_failure", "never")
IsolationLevel = _enum("IsolationLevel", "none", "process", "sandbox")
CapabilityKind = _enum("CapabilityKind", "hardware", "software", "privilege")

EquivalenceRelation = _enum(
    "EquivalenceRelation",
    "exact",
    "bisimulation",
    "weak_bisimulation",
    "observational",
    "refinement_only",
)
ProjectionSource = _enum(
    "ProjectionSource",
    "output",
    "return_value",
    "errno",
    "side_effect",
    "trace",
)
DischargeStrategy = _enum("DischargeStrategy", "witness", "differential_test", "fuzzing", "manual_review")
ContractSplitRule = _enum("ContractSplitRule", "conjunctive", "per_observable", "custom")
RecombinationKind = _enum("RecombinationKind", "conjunction", "sequence", "custom", "hoare")
HoareRuleKind = _enum(
    "HoareRuleKind",
    "assign",
    "if",
    "let",
    "quant_forall",
    "quant_exists_finite",
    "seq",
    "while",
    "call",
    "skip",
    "consequence",
    "return",
)
TripleRefRole = _enum("TripleRefRole", "premise", "conclusion", "parent")
PredicateRefOwner = _enum("PredicateRefOwner", "sub_part", "interface", "loop", "parent")
PredicateRefKind = _enum(
    "PredicateRefKind",
    "pre",
    "post",
    "intermediate",
    "invariant",
    "variant",
    "shared_post",
    "exit",
    "normal_post",
)
ContextSplitKind = _enum("ContextSplitKind", "partition", "cover", "custom")

ExtendedBehaviorClass = _enum(
    "ExtendedBehaviorClass",
    "safety",
    "invariant",
    "bounded_latency",
    "refinement",
    "trace",
    "assertion",
    "termination",
    "equivalence",
)
InjectionPolicy = _enum(
    "InjectionPolicy",
    "minimal",
    "standard",
    "thorough",
    "comprehensive",
    "equivalence_complete",
    "refinement_complete",
)
CheckProvenance = _enum("CheckProvenance", "injected", "explicit")
TemplateTier = _enum("TemplateTier", "U", "S", "C", "X", "E", "L")
TemplateTrigger = _enum(
    "TemplateTrigger",
    "always",
    "field_present",
    "metadata_match",
    "dependency_present",
    "baseline_abi_present",
    "abstraction_present",
)
InstantiationCardinality = _enum("InstantiationCardinality", "single", "per_element")

ContextGeneratorKind = _enum("ContextGeneratorKind", "enumerative", "random", "symbolic", "hybrid")
SealingMechanism = _enum("SealingMechanism", "fresh_init", "fork_from_clean_snapshot", "checkpoint_restore")

AbstractionLayerId = _enum("AbstractionLayerId", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8")
FunctionTechnique = _enum(
    "FunctionTechnique",
    "ila",
    "contract",
    "predicate_abstraction",
    "summary",
    "selective_symbolization",
    "hierarchical_ila",
)

SubPartKind = _enum(
    "SubPartKind",
    "seq_segment",
    "while_body",
    "if_then_branch",
    "if_else_branch",
    "let_body",
    "while_header",
    "while_exit",
    "other",
)
PropertyRefKind = _enum("PropertyRefKind", "explicit", "injected")
ConsequenceDirection = _enum("ConsequenceDirection", "weaken_pre", "strengthen_post")
InterfaceRelationKind = _enum("InterfaceRelationKind", "call", "sibling_branches", "sequence")

GlobalPropertyClass = _enum("GlobalPropertyClass", "G1", "G2", "G3", "G4")
EmergentMethod = _enum("EmergentMethod", "heuristic", "manual", "smt")
ResourceKind = _enum("ResourceKind", "memory", "device", "channel", "lock")
SchedulerPolicy = _enum("SchedulerPolicy", "round_robin", "priority", "fifo", "custom")
ProtocolOrdering = _enum("ProtocolOrdering", "fifo", "causal", "unordered")
GluingSeedSource = _enum("GluingSeedSource", "local_conjunction", "explicit", "synthesized")
DecompositionStage = _enum("DecompositionStage", "raw", "injected", "projected", "checked", "composed")

LoopKind = _enum("LoopKind", "for", "while", "do_while", "iterator", "recursion")
DesugaredFrom = _enum("DesugaredFrom", "for_range", "for_c", "do_while", "iterator")
InvariantFamily = _enum("InvariantFamily", "shape", "boundary", "counting", "progress", "rank")
InvariantScope = _enum("InvariantScope", "body", "driver", "exit", "all")
WellFounded = _enum("WellFounded", "proved", "disproved", "unknown")
LoopOptimizationKind = _enum(
    "LoopOptimizationKind",
    "licm",
    "induction_var",
    "unroll",
    "fusion",
    "fission",
    "strength_reduction",
    "partial_eval",
    "peeling",
    "normalization",
)
TraceStepKind = _enum("TraceStepKind", "identity", "inline", "reorder", "eliminate")
BoundedIterationKind = _enum("BoundedIterationKind", "loop", "recursion", "allocation")
BoundSource = _enum("BoundSource", "size_budget", "config_param", "wcet_model", "explicit")
OnExceed = _enum("OnExceed", "assert", "stutter", "fail")

# --------------------------------------------------------------------------- #
# §10–§12 configuration / board / profile
# --------------------------------------------------------------------------- #

ConfigType = _enum("ConfigType", "bool", "int", "string", "enum", "list")
ConfigScope = _enum("ConfigScope", "compile_time", "runtime", "both")
ConfigSeverity = _enum("ConfigSeverity", "error", "warning")
ClockSource = _enum("ClockSource", "pll", "osc", "external")

# --------------------------------------------------------------------------- #
# §9.1 lowering sub-records
# --------------------------------------------------------------------------- #

RustStrategy = _enum("RustStrategy", "best_fit", "first_fit", "worst_fit", "segregated_fit", "llm_assisted")
UnsafePolicy = _enum("UnsafePolicy", "minimal", "allowed", "forbidden")
ChannelImpl = _enum("ChannelImpl", "ring_buffer", "message_queue", "shared_memory")
DoorbellImpl = _enum("DoorbellImpl", "mmio", "mailbox", "interrupt")
SyncImpl = _enum("SyncImpl", "atomic", "futex", "semaphore")
RestartBackoff = _enum("RestartBackoff", "none", "linear", "exponential")
SaturationPolicy = _enum("SaturationPolicy", "fail", "retry", "grow")
ReproStrategy = _enum("ReproStrategy", "deterministic", "llm_assisted")
RefinementStrategy = _enum("RefinementStrategy", "web", "ila", "contract", "predicate", "summary")
PrimaryTool = _enum("PrimaryTool", "verus", "kani", "smack", "rem", "none")
LlmTool = _enum("LlmTool", "kapilot", "kverus", "starverus", "autoverus", "none")
ContextPolicy = _enum("ContextPolicy", "auto", "explicit", "disabled")
LoopOptPolicy = _enum("LoopOptPolicy", "off", "canonicalize", "aggressive")
RecombinationPolicy = _enum("RecombinationPolicy", "structural", "explicit", "disabled")
ExitStatePolicy = _enum("ExitStatePolicy", "disabled", "explicit", "cps_normalized")
SeqCompositionPolicy = _enum("SeqCompositionPolicy", "normal_post", "legacy")
PromotionPolicy = _enum("PromotionPolicy", "off", "threshold")
DagSerialization = _enum("DagSerialization", "inline", "embedded", "external")

# --------------------------------------------------------------------------- #
# literals for compact inline sets (operators etc.)
# --------------------------------------------------------------------------- #

ConfigOperator = Literal["==", "!=", ">", "<", ">=", "<=", "in"]
Relation = Literal["eq", "le", "ge", "subset", "refines", "protocol"]
