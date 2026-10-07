"""Loop analysis layer records (§9.19)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import (
    BoundedIterationKind,
    BoundSource,
    DecreaseMode,
    DesugaredFrom,
    InvariantFamily,
    InvariantScope,
    LoopKind,
    LoopOptimizationKind,
    OnExceed,
    TraceStepKind,
    WellFounded,
)
from litespec.schema.primitives import Identifier, LIRNodeRef, WitnessArtifact


class LoopInvariantClause(LiteSpecModel):
    """§9.19 ``LoopInvariantClause``."""

    family: InvariantFamily
    expr: str
    scope: InvariantScope
    rationale: Optional[str] = None
    discharged_by: Optional[Identifier] = None


class LoopVariant(LiteSpecModel):
    """§9.19 ``LoopVariant``."""

    expr: str
    domain: str
    decreases_on: DecreaseMode
    well_founded: WellFounded
    evidence: Optional[WitnessArtifact] = None


class BoundedIteration(LiteSpecModel):
    """§9.19 ``BoundedIteration``."""

    target: Identifier
    kind: BoundedIterationKind
    bound: int
    bound_source: BoundSource
    on_exceed: OnExceed


class LoopOptimization(LiteSpecModel):
    """§9.19 ``LoopOptimization``."""

    kind: LoopOptimizationKind
    params: Optional[dict[str, object]] = None
    soundness: str
    certificate: WitnessArtifact


class TraceabilityStep(LiteSpecModel):
    """§9.19 ``TraceabilityStep``."""

    source_span: str
    opt_span: str
    kind: TraceStepKind


class LoopTraceability(LiteSpecModel):
    """§9.19 ``LoopTraceability``."""

    source_to_optimized: list[TraceabilityStep] = []
    source_hash: str
    optimized_hash: str


class LoopAnalysis(LiteSpecModel):
    """§9.19 ``LoopAnalysis``."""

    loop_id: Identifier
    function: Identifier
    lir_fragment: LIRNodeRef
    loop_kind: LoopKind
    desugared_from: Optional[DesugaredFrom] = None
    iteration_var: Optional[Identifier] = None
    parent_loop: Optional[Identifier] = None
    inner_loops: list[Identifier] = []
    header_state: list[Identifier] = []
    body_state: list[Identifier] = []
    exit_state: list[Identifier] = []
    invariant_clauses: list[LoopInvariantClause] = []
    variant: Optional[LoopVariant] = None
    bound: Optional[BoundedIteration] = None
    optimizations: list[LoopOptimization] = []
    traceability: Optional[LoopTraceability] = None
