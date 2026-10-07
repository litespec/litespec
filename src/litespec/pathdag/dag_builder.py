"""Path-condition DAG construction (D78 ``DerivePathConditionDAG``).

Applies to a desugared ``EffectExpr`` (post Stage-1/Stage-2): ``ForCExpr`` must
already be desugared by D84. Produces the node structure whose top-level
``seq``-nodes match §18.1 (one per segment of the desugared ``ForCExpr``).
"""

from __future__ import annotations

import itertools
from typing import Callable, Optional

from litespec.lir.effect_expr_ast import (
    Conditional,
    DoWhile,
    EffectExpr,
    ForC,
    ForRange,
    Iterator,
    Return,
    Sequence,
    While,
    render_expr,
)
from litespec.schema.enums import PathNodeKind
from litespec.schema.path_condition_dag import PathConditionDAG, PathNode
from litespec.schema.primitives import Predicate

FallthroughFn = Callable[[EffectExpr, int], str]


def _mk_node(node_id: str, parent: Optional[str], kind: str, expr: str, desc: str) -> PathNode:
    return PathNode(
        node_id=node_id,
        indicator="",  # placeholder; D81 assigns the canonical indicator
        parent=parent,
        guard=Predicate(expression=expr, description=desc),
        kind=PathNodeKind(kind),
    )


def _scan_returns(effect: EffectExpr, parent: str, nodes: list[PathNode], gen) -> None:
    """Collect ``return`` nodes reachable inside a loop body (break/continue are
    desugared into exit-state disjuncts by D76 and are out of scope here)."""
    if isinstance(effect, Return):
        nodes.append(_mk_node(next(gen), parent, "return", "true", "Return path"))
        return
    for child in _children(effect):
        _scan_returns(child, parent, nodes, gen)


def _children(effect: EffectExpr) -> tuple[EffectExpr, ...]:
    if isinstance(effect, Sequence):
        return effect.items
    if isinstance(effect, While):
        return (effect.body,)
    if isinstance(effect, Conditional):
        return (effect.then, effect.else_)
    if isinstance(effect, DoWhile):
        return (effect.body,)
    if isinstance(effect, ForRange):
        return (effect.body,)
    if isinstance(effect, Iterator):
        return (effect.body,)
    if isinstance(effect, ForC):
        return (effect.body,)
    return ()


def _walk(
    effect: EffectExpr,
    parent: Optional[str],
    nodes: list[PathNode],
    gen,
    fallthrough: FallthroughFn,
) -> None:
    if isinstance(effect, Sequence):
        segs = effect.items
        if not segs:
            return
        first = _mk_node(next(gen), parent, "seq", "true", "Segment 1 entry")
        nodes.append(first)
        _walk_leaves(segs[0], first.node_id, nodes, gen, fallthrough)
        prev = first
        for i in range(1, len(segs)):
            guard_expr = fallthrough(segs[i - 1], i) if fallthrough else "true"
            seq = _mk_node(next(gen), prev.node_id, "seq", guard_expr, f"Segment {i + 1} reachability")
            nodes.append(seq)
            _walk(segs[i], seq.node_id, nodes, gen, fallthrough)
            prev = seq
        return

    if isinstance(effect, While):
        cond = render_expr(effect.cond)
        body = _mk_node(next(gen), parent, "loop_body", cond, "Loop body guard")
        exit_ = _mk_node(next(gen), parent, "loop_exit", f"not ({cond})", "Loop exit")
        nodes.append(body)
        nodes.append(exit_)
        _scan_returns(effect.body, body.node_id, nodes, gen)
        return

    if isinstance(effect, Conditional):
        cond = render_expr(effect.cond)
        then = _mk_node(next(gen), parent, "branch_then", cond, "Then-guard")
        else_ = _mk_node(next(gen), parent, "branch_else", f"not ({cond})", "Else-guard")
        nodes.append(then)
        nodes.append(else_)
        _walk(effect.then, then.node_id, nodes, gen, fallthrough)
        _walk(effect.else_, else_.node_id, nodes, gen, fallthrough)
        return

    if isinstance(effect, (DoWhile, ForRange, Iterator)):
        # These are desugared by ProgressiveLoweringPass (Stage 1) before D78.
        cond = render_expr(effect.cond) if isinstance(effect, DoWhile) else "true"
        body = _mk_node(next(gen), parent, "loop_body", cond, "Loop body guard")
        exit_ = _mk_node(next(gen), parent, "loop_exit", f"not ({cond})", "Loop exit")
        nodes.append(body)
        nodes.append(exit_)
        return

    if isinstance(effect, ForC):
        raise ValueError("ForCExpr not desugared before path-DAG construction (for_c_stage2_undeclared)")

    if isinstance(effect, Return):
        nodes.append(_mk_node(next(gen), parent, "return", "true", "Return path"))
        return

    # Leaf: Assignment / ExprStmt / Skip / Let / Quantified / CallEffect / Guard / SetUpdate
    # (D78 produces no node for these).


def _walk_leaves(
    effect: EffectExpr,
    parent: Optional[str],
    nodes: list[PathNode],
    gen,
    fallthrough: FallthroughFn,
) -> None:
    """Walk a single segment's non-``seq`` structure (branch/loop/return nodes)."""
    if isinstance(effect, Sequence) or isinstance(effect, (While, Conditional, DoWhile, ForRange, Iterator)):
        _walk(effect, parent, nodes, gen, fallthrough)
    elif isinstance(effect, Return):
        nodes.append(_mk_node(next(gen), parent, "return", "true", "Return path"))
    # leaves otherwise


def build_path_dag(
    effect: EffectExpr,
    dag_id: str,
    *,
    root_id: str = "n_root",
    fallthrough: Optional[FallthroughFn] = None,
) -> PathConditionDAG:
    """Derive a ``PathConditionDAG`` from a desugared ``EffectExpr`` (D78)."""
    nodes: list[PathNode] = []
    gen = (f"n{i}" for i in itertools.count())
    entry = PathNode(
        node_id=root_id,
        indicator="",
        parent=None,
        guard=Predicate(expression="true", description="Function entry"),
        kind=PathNodeKind("entry"),
    )
    nodes.append(entry)
    _walk(effect, entry.node_id, nodes, gen, fallthrough)
    return PathConditionDAG(dag_id=dag_id, nodes=nodes, root=entry.node_id)
