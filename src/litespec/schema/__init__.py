"""LiteSpec wire-format schema (§3–§12) as Pydantic v2 models."""

from litespec.schema.abstraction_block import (
    AbstractionBlock,
    AbstractionLayer,
    AbstractionRelation,
    DialectStack,
    ISIRTarget,
    RankWitness,
)
from litespec.schema.base import LiteSpecModel
from litespec.schema.board_configuration import (
    BoardConfiguration,
    CacheConfig,
    ClockDomainConfig,
    CPUConfig,
    MemoryConfig,
    PeripheralConfig,
    PowerDomainConfig,
)
from litespec.schema.configuration_layer import (
    ConfigCondition,
    ConfigConstraint,
    ConfigDefaults,
    ConfigGroup,
    ConfigParameter,
    ConfigPreset,
    ConfigurationLayer,
    Range,
    RuntimeAPI,
)
from litespec.schema.contract_layer import (
    ABICompatibility,
    ABIEntry,
    AssemblyContract,
    AtomicInstruction,
    ContractLayer,
    MemoryFence,
    PerformanceContract,
    PriorityInheritanceContract,
    PriorityInvariant,
    RegisterConstraint,
    SideEffect,
    WCETModel,
)
from litespec.schema.contract_layer import (
    LoopInvariantClause as ContractLoopInvariantClause,
)
from litespec.schema.decomposition_block import (
    DecompositionBlock,
    InterfacePropertyCheck,
    NestedSharedPost,
    PropertyLattice,
    RecombinationRule,
    SubPart,
)
from litespec.schema.decomposition_context import (
    ContextualSubPart,
    DecompositionContext,
    EquivalenceSplit,
    ExitStateContext,
    GluingSeed,
    InjectionProjection,
    LoopContext,
    SpecRecordRef,
)
from litespec.schema.document import (
    BoundingMetadata,
    BuildProfile,
    DependencyBudget,
    LiteSpecDocument,
    LLMPolicy,
    LLMProvenanceRecord,
    ModuleHeader,
    ProfileRef,
    ProfileValidation,
    SizeBudget,
    SpecRecord,
    VerificationBudget,
)
from litespec.schema.equivalence_model import (
    AssumptionSet,
    CommonFunctionality,
    ContextGenerator,
    ContextSplitRule,
    ContextSubset,
    CoverageTarget,
    DependencyAssumption,
    EquivalenceDecomposition,
    EquivalenceModel,
    EquivalenceSubPart,
    ExtendedFunctionality,
    FunctionalSurface,
    Guarantee,
    GuaranteeSet,
    ObservableProjection,
    SealingModel,
    Tolerance,
)
from litespec.schema.exit_state import ExitDisjunct, ExitState, ExitStateModel, ProvenanceMap
from litespec.schema.extended_behavior import (
    ExtendedBehaviorCheck,
    ExtendedBehaviorModel,
    InjectionReportProjection,
)
from litespec.schema.fragment_complexity import FragmentComplexity
from litespec.schema.global_property_block import (
    CompositionSpec,
    EmergentDetection,
    GlobalProperty,
    GlobalPropertyBlock,
    GluingInvariant,
    InterfaceSpec,
    ProtocolSpec,
    Resource,
    SchedulerSpec,
)
from litespec.schema.hardware import (
    ClockDomain,
    HardwareEncodingLayer,
    HWAssertion,
    Signal,
    TransitionCycle,
    TypeEncoding,
)
from litespec.schema.hoare_triple import (
    ControlFlowSet,
    HoareRuleRef,
    HoareTriple,
    HoareTripleRef,
    ParentHoareTriple,
    PredicateRef,
)
from litespec.schema.ipc import Doorbell, IPCChannel, IPCLayer, SyncPrimitive
from litespec.schema.loop_analysis import (
    BoundedIteration,
    LoopAnalysis,
    LoopInvariantClause,
    LoopOptimization,
    LoopTraceability,
    LoopVariant,
    TraceabilityStep,
)
from litespec.schema.lowering_metadata import LoweringMetadata
from litespec.schema.path_condition_dag import (
    InlineAxiomStream,
    PathConditionDAG,
    PathDAGArtifact,
    PathDagOp,
    PathDAGSerialization,
    PathNode,
)
from litespec.schema.primitives import (
    ConfigExpr,
    ConsequenceStep,
    GrammarImport,
    HashBinding,
    HashBindingsBlock,
    LIRNodeRef,
    Predicate,
    PropertyRef,
    WitnessArtifact,
)
from litespec.schema.property_templates import InstantiationRule, PropertyTemplate
from litespec.schema.service_interface import ServiceDependency, ServiceInterface, ServiceOperation
from litespec.schema.source_layer import SourceLayer
from litespec.schema.state_machine_layer import Action, InitPredicate, StateMachineLayer, StateVar, StateVarRange
from litespec.schema.syscall_mapping import SyscallMapping
from litespec.schema.target_profile import ABIReference, TargetProfile
from litespec.schema.type_expressions import (
    PRIMITIVE_TYPES,
    TypeDeclaration,
    TypeExpr,
    format_type_expr,
    parse_type_expr,
)
from litespec.schema.verification_layer import (
    CapabilityContractRef,
    ProofObligation,
    Property,
    RefinementObligation,
    VerificationLayer,
    VerifyTarget,
)

__all__ = [name for name in dir() if not name.startswith("_")]
