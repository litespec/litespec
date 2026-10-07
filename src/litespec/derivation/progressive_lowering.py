"""D77 ``DeriveLoopConstructDesugaring``: lower non-``ForC`` loops to ``While``.

``ForCExpr`` is retained as a Stage-2 construct (desugared by D84). ``ForRange``,
``DoWhile``, and ``Iterator`` lower to ``SequenceExpr``/``WhileExpr`` forms.
"""

from __future__ import annotations

from litespec.lir.effect_expr_ast import (
    Call,
    CallEffect,
    DoWhile,
    EffectExpr,
    ForC,
    ForRange,
    Iterator,
    Sequence,
    Var,
    While,
)


def _has_next(var: str) -> Call:
    return Call("has_next", (Var(var),))


def _advance(var: str) -> CallEffect:
    return CallEffect("advance", (Var(var),))


def derive_loop_construct_desugaring(c: EffectExpr) -> tuple[EffectExpr, str]:
    """Desugar one loop constructor (D77). Returns ``(effect, note)``."""
    if isinstance(c, ForRange):
        iter_var = c.name
        iterator_init = CallEffect("MakeIterator", (Var(iter_var),))
        inner = Sequence((c.body, _advance(iter_var)))
        return Sequence((iterator_init, While(_has_next(iter_var), inner))), (
            "for_range -> iterator; while has_next do body; advance"
        )
    if isinstance(c, ForC):
        return c, "for_c retained as a Stage-2 construct; desugared by D84"
    if isinstance(c, DoWhile):
        return Sequence((c.body, While(c.cond, c.body))), "do_while -> body; while guard do body"
    if isinstance(c, Iterator):
        iter_var = c.name
        inner = Sequence((c.body, _advance(iter_var)))
        return While(_has_next(iter_var), inner), "iterator -> while has_next do body; advance"
    return c, "no desugaring"


def progressive_lower(e: EffectExpr) -> EffectExpr:
    """Recursively lower non-``ForC`` loops (ProgressiveLoweringPass, Stage 1)."""
    lowered, _ = derive_loop_construct_desugaring(e)
    if lowered is not e:
        return progressive_lower(lowered)
    if isinstance(e, Sequence):
        return Sequence(tuple(progressive_lower(c) for c in e.items))
    if isinstance(e, While):
        return While(e.cond, progressive_lower(e.body))
    from litespec.lir.effect_expr_ast import Conditional, Let, Quantified

    if isinstance(e, Conditional):
        return Conditional(e.cond, progressive_lower(e.then), progressive_lower(e.else_))
    if isinstance(e, Let):
        return Let(e.name, e.type, progressive_lower(e.value), progressive_lower(e.body))
    if isinstance(e, Quantified):
        return Quantified(e.quantifier, e.name, e.type, e.domain, progressive_lower(e.body))
    if isinstance(e, ForC):
        return ForC(e.name, e.type, e.init, e.guard, e.step, progressive_lower(e.body))
    return e
