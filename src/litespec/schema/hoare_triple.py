"""Hoare-triple records (§3, §9.16)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import ControlFlow, HoareRuleKind, PredicateRefKind, PredicateRefOwner, TripleRefRole
from litespec.schema.primitives import ConsequenceStep, Identifier, LIRNodeRef, NodeId, Predicate


class HoareTripleRef(LiteSpecModel):
    """§9.8 ``HoareTripleRef ::= { sub_part, role }``."""

    sub_part: Identifier
    role: TripleRefRole


class PredicateRef(LiteSpecModel):
    """§9.8 ``PredicateRef ::= { owner, owner_ref, kind, ref }``."""

    owner: PredicateRefOwner
    owner_ref: Identifier
    kind: PredicateRefKind
    ref: Identifier


class HoareRuleRef(LiteSpecModel):
    """§9.8 ``HoareRuleRef ::= { rule, premise_refs, intermediate_ref?, conclusion_ref }``."""

    rule: HoareRuleKind
    premise_refs: list[HoareTripleRef] = []
    intermediate_ref: Optional[PredicateRef] = None
    conclusion_ref: HoareTripleRef


class ControlFlowSet(LiteSpecModel):
    """§3 ``ControlFlowSet ::= { members }``."""

    members: list[ControlFlow] = []


class HoareTriple(LiteSpecModel):
    """§9.16 ``HoareTriple``."""

    sub_part_ref: Identifier
    command_ref: LIRNodeRef
    pre: Predicate
    post: Predicate
    rule: HoareRuleRef
    callee: Optional[Identifier] = None
    arguments: Optional[list[str]] = None
    consequence: Optional[list[ConsequenceStep]] = None
    exit_state: Optional[ExitState] = None
    control_flow: ControlFlowSet = ControlFlowSet()


class ParentHoareTriple(LiteSpecModel):
    """§3 ``ParentHoareTriple``."""

    command_ref: LIRNodeRef
    pre: Predicate
    post: Predicate
    rule: HoareRuleRef
    consequence: Optional[list[ConsequenceStep]] = None
    exit_state: Optional[ExitState] = None
    control_flow: ControlFlowSet = ControlFlowSet()
    path_ref: Optional[NodeId] = None


from litespec.schema.exit_state import ExitState

HoareTriple.model_rebuild()
ParentHoareTriple.model_rebuild()
