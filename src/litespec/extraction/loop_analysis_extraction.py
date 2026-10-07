"""Loop-analysis extraction (D65 ``DeriveLoopAnalysis``)."""

from __future__ import annotations

from litespec.lir.effect_expr_ast import DoWhile, EffectExpr, ForC, ForRange, Iterator, Sequence, While
from litespec.schema.loop_analysis import LoopAnalysis
from litespec.schema.primitives import LIRNodeRef


def collect_loop_analyses(effect: EffectExpr, function: str) -> list[LoopAnalysis]:
    """Collect ``LoopAnalysis`` records for every loop constructor in ``effect``."""
    loops: list[LoopAnalysis] = []
    _collect(effect, function, loops, None)
    return loops


def _collect(effect: EffectExpr, function: str, loops: list[LoopAnalysis], parent: str | None) -> None:
    loop_kind = None
    desugared_from = None
    if isinstance(effect, While):
        loop_kind = "while"
    elif isinstance(effect, ForC):
        loop_kind = "for"
        desugared_from = "for_c"
    elif isinstance(effect, ForRange):
        loop_kind = "for"
        desugared_from = "for_range"
    elif isinstance(effect, DoWhile):
        loop_kind = "do_while"
    elif isinstance(effect, Iterator):
        loop_kind = "iterator"

    if loop_kind is not None:
        loop_id = f"{function}_loop_{len(loops) + 1}"
        loops.append(
            LoopAnalysis(
                loop_id=loop_id,
                function=function,
                lir_fragment=LIRNodeRef(function=function, node_id=loop_id),
                loop_kind=loop_kind,
                desugared_from=desugared_from,
                parent_loop=parent,
            )
        )
        parent = loop_id

    for child in _children(effect):
        _collect(child, function, loops, parent)


def _children(effect: EffectExpr) -> tuple[EffectExpr, ...]:
    if isinstance(effect, Sequence):
        return effect.items
    if isinstance(effect, While):
        return (effect.body,)
    if isinstance(effect, ForC):
        return (effect.init, effect.step, effect.body)
    if isinstance(effect, ForRange):
        return (effect.body,)
    if isinstance(effect, DoWhile):
        return (effect.body,)
    if isinstance(effect, Iterator):
        return (effect.body,)
    from litespec.lir.effect_expr_ast import Conditional, Let, Quantified

    if isinstance(effect, Conditional):
        return (effect.then, effect.else_)
    if isinstance(effect, Let):
        return (effect.value, effect.body)
    if isinstance(effect, Quantified):
        return (effect.body,)
    return ()
