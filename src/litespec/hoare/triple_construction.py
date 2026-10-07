"""Sub-part / Hoare-triple construction helpers (D67 ``mk_sub``, ``synthetic_node``)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.decomposition_block import SubPart
from litespec.schema.exit_state import ExitState
from litespec.schema.hoare_triple import (
    ControlFlowSet,
    HoareRuleRef,
    HoareTriple,
    HoareTripleRef,
)
from litespec.schema.primitives import LIRNodeRef, Predicate


def synthetic_node(parent: LIRNodeRef, role: str) -> LIRNodeRef:
    """§9.21.3 ``synthetic_node(parent_node, role)``."""
    return LIRNodeRef(function=parent.function, node_id=f"{parent.node_id}::{role}")


def premise_ref(name: str) -> HoareTripleRef:
    return HoareTripleRef(sub_part=name, role="premise")


def conclusion_ref(name: str) -> HoareTripleRef:
    return HoareTripleRef(sub_part=name, role="conclusion")


def parent_ref() -> HoareTripleRef:
    return HoareTripleRef(sub_part="__parent__", role="parent")


def mk_sub(
    name: str,
    node: LIRNodeRef,
    kind: str,
    pre: Predicate,
    post: Predicate,
    rule: HoareRuleRef,
    *,
    exit_state: Optional[ExitState] = None,
    control_flow: Optional[ControlFlowSet] = None,
    callee: Optional[str] = None,
    arguments: Optional[list[str]] = None,
) -> SubPart:
    """§9.21.3 ``mk_sub``."""
    triple = HoareTriple(
        sub_part_ref=name,
        command_ref=node,
        pre=pre,
        post=post,
        rule=rule,
        callee=callee,
        arguments=arguments,
        exit_state=exit_state,
        control_flow=control_flow or ControlFlowSet(members=["normal"]),
    )
    return SubPart(
        name=name,
        lir_fragment=node,
        kind=kind,  # type: ignore[arg-type]
        properties=[],
        technique="contract",  # type: ignore[arg-type]
        required_layers=[],
        hoare_triple=triple,
    )
