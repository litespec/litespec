"""D67 ``DeriveHoareDecomposition`` (§9.21.3).

Recursively decomposes a desugared ``EffectExpr`` into a flat, path-qualified
list of ``SubPart`` records with attached ``HoareTriple``/``HoareRuleRef``, plus
``InterfacePropertyCheck`` records. Compound branches (``seq``, ``while``,
``if``, ``let``, quantified) are recursively closed. Sub-parts are emitted in
pre-order (parent before children), matching §18.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from litespec.hoare.correctness_propagation import correctness_of_rule
from litespec.hoare.possible_outcomes import possible_outcomes_of_subpart
from litespec.hoare.rule_reference import rule_of_command
from litespec.hoare.triple_construction import conclusion_ref, parent_ref, premise_ref, synthetic_node
from litespec.lir.effect_expr_ast import (
    CallEffect,
    Conditional,
    EffectExpr,
    Let,
    Quantified,
    Sequence,
    Skip,
    While,
    render_expr,
)
from litespec.schema.decomposition_block import InterfacePropertyCheck, SubPart
from litespec.schema.hoare_triple import (
    ControlFlowSet,
    HoareRuleRef,
    HoareTriple,
    HoareTripleRef,
    ParentHoareTriple,
    PredicateRef,
)
from litespec.schema.primitives import LIRNodeRef, Predicate, WitnessArtifact


@dataclass
class HoareDecompositionResult:
    sub_parts: list[SubPart]
    interface_checks: list[InterfacePropertyCheck]
    parent_triple: ParentHoareTriple
    rule: str
    correctness: str


@dataclass
class _Accumulator:
    sub_parts: list[SubPart] = field(default_factory=list)
    interface_checks: list[InterfacePropertyCheck] = field(default_factory=list)


def _pred(expr: str, desc: str = "", name: Optional[str] = None) -> Predicate:
    return Predicate(expression=expr, description=desc or expr, name=name)


def _evidence(icid: str) -> WitnessArtifact:
    return WitnessArtifact(kind="proof", uri=f"evidence/{icid}.json", hash="0" * 64)


def _seq_interface_checks(child_names: list[str], acc: _Accumulator) -> Optional[PredicateRef]:
    """Emit one interface check per sequence boundary; return the first intermediate ref."""
    first: Optional[PredicateRef] = None
    for i in range(len(child_names) - 1):
        iname = f"R_{child_names[i].replace('::', '_')}_done"
        icid = f"{child_names[i]}__{child_names[i + 1]}"
        acc.interface_checks.append(
            InterfacePropertyCheck(
                id=icid,
                caller=child_names[i],
                callee=child_names[i + 1],
                relation_kind="sequence",
                required=[],
                provided=[],
                evidence=_evidence(icid),
                intermediate_assertion=_pred(iname, f"Normal post of {child_names[i]}", name=iname),
            )
        )
        if i == 0:
            first = PredicateRef(owner="interface", owner_ref=icid, kind="normal_post", ref=iname)
    return first


def _decompose(
    effect: EffectExpr,
    name: str,
    node: LIRNodeRef,
    kind: str,
    pre: Predicate,
    post: Predicate,
    acc: _Accumulator,
) -> SubPart:
    rule = rule_of_command(effect)
    premises: list[HoareTripleRef] = []
    intermediate: Optional[PredicateRef] = None
    callee: Optional[str] = None
    arguments: Optional[list[str]] = None
    child_specs: list[tuple[EffectExpr, str, LIRNodeRef, str]] = []

    if isinstance(effect, Sequence):
        segs = list(effect.items)
        for i, seg in enumerate(segs, start=1):
            cname = f"{name}::seq_seg_{i}" if name else f"seq_part_{i}"
            child_specs.append((seg, cname, synthetic_node(node, f"seg_{i}"), "seq_segment"))
        premises = [premise_ref(cname) for _, cname, _, _ in child_specs]
        intermediate = _seq_interface_checks([cname for _, cname, _, _ in child_specs], acc)

    elif isinstance(effect, While):
        header_name = f"{name}::while_header"
        body_name = f"{name}::while_body"
        exit_name = f"{name}::while_exit"
        child_specs = [
            (Skip(), header_name, synthetic_node(node, "while_header"), "while_header"),
            (effect.body, body_name, synthetic_node(node, "while_body"), "while_body"),
            (Skip(), exit_name, synthetic_node(node, "while_exit"), "while_exit"),
        ]
        premises = [premise_ref(body_name)]
        intermediate = PredicateRef(
            owner="interface",
            owner_ref=f"{body_name}__{header_name}",
            kind="invariant",
            ref=f"I_{name or 'loop'}",
        )

    elif isinstance(effect, Conditional):
        then_name = f"{name}::if_then"
        else_name = f"{name}::if_else"
        child_specs = [
            (effect.then, then_name, synthetic_node(node, "if_then"), "if_then_branch"),
            (effect.else_, else_name, synthetic_node(node, "if_else"), "if_else_branch"),
        ]
        premises = [premise_ref(then_name), premise_ref(else_name)]

    elif isinstance(effect, Let):
        body_name = f"{name}::let_body"
        child_specs = [(effect.body, body_name, synthetic_node(node, "let_body"), "let_body")]
        premises = [premise_ref(body_name)]

    elif isinstance(effect, Quantified):
        body_name = f"{name}::quant_body"
        child_specs = [(effect.body, body_name, synthetic_node(node, "quant_body"), "other")]
        premises = [premise_ref(body_name)]

    elif isinstance(effect, CallEffect):
        callee = effect.name
        arguments = [render_expr(a) for a in effect.args]

    # Emit the parent sub-part first (pre-order).
    rule_ref = HoareRuleRef(
        rule=rule, premise_refs=premises, intermediate_ref=intermediate, conclusion_ref=conclusion_ref(name)
    )
    triple = HoareTriple(
        sub_part_ref=name,
        command_ref=node,
        pre=pre,
        post=post,
        rule=rule_ref,
        callee=callee,
        arguments=arguments,
        control_flow=ControlFlowSet(),
    )
    sp = SubPart(
        name=name,
        lir_fragment=node,
        kind=kind,  # type: ignore[arg-type]
        properties=[],
        technique="contract",  # type: ignore[arg-type]
        required_layers=[],
        hoare_triple=triple,
    )
    acc.sub_parts.append(sp)

    for c_effect, c_name, c_node, c_kind in child_specs:
        _decompose(c_effect, c_name, c_node, c_kind, pre, post, acc)

    return sp


def _correctness(sp: SubPart, lookup: dict[str, SubPart], memo: dict[str, str]) -> str:
    if sp.name in memo:
        return memo[sp.name]
    rule = str(sp.hoare_triple.rule.rule)
    children = [lookup[r.sub_part] for r in sp.hoare_triple.rule.premise_refs if r.sub_part in lookup]
    child_c = [_correctness(c, lookup, memo) for c in children]
    memo[sp.name] = correctness_of_rule(rule, child_c)
    return memo[sp.name]


def derive_hoare_decomposition(
    effect: EffectExpr,
    function: str,
    pre: Optional[Predicate] = None,
    post: Optional[Predicate] = None,
) -> HoareDecompositionResult:
    """D67: decompose ``effect`` into sub-parts, interface checks, and a parent triple."""
    pre = pre or _pred("true", "Precondition")
    post = post or _pred("true", "Postcondition")
    acc = _Accumulator()
    root_node = LIRNodeRef(function=function, node_id="L_root")
    root = _decompose(effect, "", root_node, "other", pre, post, acc)

    # The root sub-part is the fragment head; project it into the parent triple.
    acc.sub_parts.remove(root)
    parent_triple = ParentHoareTriple(
        command_ref=root_node,
        pre=pre,
        post=post,
        rule=HoareRuleRef(
            rule=root.hoare_triple.rule.rule,
            premise_refs=root.hoare_triple.rule.premise_refs,
            intermediate_ref=root.hoare_triple.rule.intermediate_ref,
            conclusion_ref=parent_ref(),
        ),
        exit_state=root.hoare_triple.exit_state,
        control_flow=root.hoare_triple.control_flow,
    )

    lookup = {sp.name: sp for sp in acc.sub_parts}
    for sp in acc.sub_parts:
        outcomes = possible_outcomes_of_subpart(sp, lookup)
        sp.hoare_triple.control_flow = ControlFlowSet(members=sorted(outcomes))

    memo: dict[str, str] = {}
    children = [lookup[r.sub_part] for r in parent_triple.rule.premise_refs if r.sub_part in lookup]
    child_c = [_correctness(c, lookup, memo) for c in children]
    correctness = correctness_of_rule(str(parent_triple.rule.rule), child_c)

    return HoareDecompositionResult(
        sub_parts=acc.sub_parts,
        interface_checks=acc.interface_checks,
        parent_triple=parent_triple,
        rule=str(parent_triple.rule.rule),
        correctness=correctness,
    )
