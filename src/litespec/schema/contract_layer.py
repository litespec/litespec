"""Contract layer schema (§6)."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import (
    BoundType,
    CacheModel,
    FenceKind,
    FenceScope,
    PipelineModel,
    PriorityProtocol,
    RegisterRole,
    VerificationMethod,
    WcetMethod,
)
from litespec.schema.primitives import Identifier, Predicate


class SideEffect(LiteSpecModel):
    """§6.1 ``SideEffect ::= { name, description }``."""

    name: Identifier
    description: str


class ABIEntry(LiteSpecModel):
    """§6.1 ``ABIEntry``."""

    name: Identifier
    return_value_semantics: str
    error_codes: list[str] = []
    errno_behavior: Optional[str] = None
    parameter_order: list[str] = []
    calling_convention: Optional[str] = None
    ioctl_commands: Optional[list[str]] = None
    side_effects: Optional[list[SideEffect]] = None
    trace_relevant: Optional[bool] = None


class ABICompatibility(LiteSpecModel):
    """§6.1 ``ABICompatibility ::= { entries }``."""

    entries: list[ABIEntry] = []


class RegisterConstraint(LiteSpecModel):
    """§6.1 ``RegisterConstraint ::= { register, role, constraint? }``."""

    register_: str = Field(alias="register")
    role: RegisterRole
    constraint: Optional[str] = None


class MemoryFence(LiteSpecModel):
    """§6.1 ``MemoryFence ::= { kind, scope }``."""

    kind: FenceKind
    scope: FenceScope


class AtomicInstruction(LiteSpecModel):
    """§6.1 ``AtomicInstruction ::= { name, semantics, alignment? }``."""

    name: str
    semantics: str
    alignment: Optional[int] = None


class AssemblyContract(LiteSpecModel):
    """§6.1 ``AssemblyContract``."""

    register_constraints: list[RegisterConstraint] = []
    memory_fences: list[MemoryFence] = []
    atomic_instructions: list[AtomicInstruction] = []
    clobbers: list[str] = []


class PriorityInvariant(LiteSpecModel):
    """§6.1 ``PriorityInvariant ::= { expression, description }``."""

    expression: str
    description: str


class PriorityInheritanceContract(LiteSpecModel):
    """§6.1 ``PriorityInheritanceContract``."""

    enabled: bool
    protocol: PriorityProtocol
    transitive: bool
    invariants: list[PriorityInvariant] = []


class WCETModel(LiteSpecModel):
    """§6.1 ``WCETModel``."""

    method: WcetMethod
    entry_point: str
    call_graph: str
    cache_model: CacheModel
    pipeline_model: PipelineModel


class PerformanceContract(LiteSpecModel):
    """§6.1 ``PerformanceContract``."""

    metric: str
    expression: str
    unit: Optional[str] = None
    description: str
    verification: VerificationMethod
    bound_type: BoundType
    percentile: Optional[int] = None
    wcet_model: Optional[WCETModel] = None


class LoopInvariantClause(LiteSpecModel):
    """§6.1 ``LoopInvariantClause ::= { family, expr, scope }``."""

    family: str
    expr: str
    scope: str


class ContractLayer(LiteSpecModel):
    """§6.1 ``ContractLayer``."""

    preconditions: list[Predicate] = []
    postconditions: list[Predicate] = []
    invariants: list[Predicate] = []
    loop_invariants: Optional[list[LoopInvariantClause]] = None
    performance: list[PerformanceContract] = []
    abi_compatibility: Optional[ABICompatibility] = None
    assembly_contract: Optional[AssemblyContract] = None
    priority_inheritance: Optional[PriorityInheritanceContract] = None
    wcet_model: Optional[WCETModel] = None
    memory_fences: Optional[list[MemoryFence]] = None
    atomic_instructions: Optional[list[AtomicInstruction]] = None
