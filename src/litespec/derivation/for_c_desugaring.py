"""D84 ``DeriveForCDesugaring``: desugar a ``ForCExpr`` into a sequence + while loop."""

from __future__ import annotations

from litespec.lir.effect_expr_ast import EffectExpr, ForC, Sequence, While, fresh_rename, rename_var


def derive_for_c_desugaring(c: ForC) -> EffectExpr:
    """Desugar ``ForC(name, type, init, guard, step, body)`` (D84).

    ``SequenceExpr([init_renamed, WhileExpr(guard, SequenceExpr([body, step]))])``
    with capture-avoiding renaming of ``init`` when ``binder.name ∈ fv(init)``.
    """
    body_and_step = Sequence((c.body, c.step))
    loop = While(c.guard, body_and_step)

    init: EffectExpr = c.init
    if c.name in init.fv():
        forbidden = init.fv() | c.guard.identifiers() | c.step.fv() | c.body.fv()
        fresh = fresh_rename(c.name, forbidden)
        init = rename_var(init, c.name, fresh)

    return Sequence((init, loop))


def desugar_for_c_in(e: EffectExpr) -> EffectExpr:
    """Recursively desugar every ``ForCExpr`` in ``e`` (ForCLoweringPass, §15.10.1)."""
    if isinstance(e, ForC):
        return derive_for_c_desugaring(e)
    if isinstance(e, Sequence):
        return Sequence(tuple(desugar_for_c_in(c) for c in e.items))
    if isinstance(e, While):
        return While(e.cond, desugar_for_c_in(e.body))
    from litespec.lir.effect_expr_ast import Conditional, DoWhile, ForRange, Iterator, Let, Quantified

    if isinstance(e, Conditional):
        return Conditional(e.cond, desugar_for_c_in(e.then), desugar_for_c_in(e.else_))
    if isinstance(e, Let):
        return Let(e.name, e.type, desugar_for_c_in(e.value), desugar_for_c_in(e.body))
    if isinstance(e, Quantified):
        return Quantified(e.quantifier, e.name, e.type, e.domain, desugar_for_c_in(e.body))
    if isinstance(e, DoWhile):
        return DoWhile(desugar_for_c_in(e.body), e.cond)
    if isinstance(e, ForRange):
        return ForRange(e.name, e.type, e.iterable, desugar_for_c_in(e.body))
    if isinstance(e, Iterator):
        return Iterator(e.name, e.type, e.iterable, desugar_for_c_in(e.body))
    return e
