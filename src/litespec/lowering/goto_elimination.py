"""Forward-goto elimination (Phase 4): ``__goto_L``/``__label_L`` → Rust labeled blocks."""

from __future__ import annotations

from litespec.lir.effect_expr_ast import (
    BreakLabel,
    Conditional,
    DoWhile,
    EffectExpr,
    ExprStmt,
    ForC,
    ForRange,
    Iterator,
    LabeledBlock,
    Let,
    Quantified,
    Sequence,
    Var,
    While,
)


def _is_label(effect: EffectExpr) -> str | None:
    if isinstance(effect, ExprStmt) and isinstance(effect.expr, Var) and effect.expr.name.startswith("__label_"):
        return effect.expr.name[len("__label_") :]
    return None


def _rewrite_goto(effect: EffectExpr, label: str) -> EffectExpr:
    """Replace ``ExprStmt(Var('__goto_L'))`` with ``BreakLabel('L')``, recursively."""
    if isinstance(effect, ExprStmt) and isinstance(effect.expr, Var) and effect.expr.name == f"__goto_{label}":
        return BreakLabel(label)
    if isinstance(effect, Sequence):
        return Sequence(tuple(_rewrite_goto(i, label) for i in effect.items))
    if isinstance(effect, Conditional):
        return Conditional(effect.cond, _rewrite_goto(effect.then, label), _rewrite_goto(effect.else_, label))
    if isinstance(effect, While):
        return While(effect.cond, _rewrite_goto(effect.body, label))
    if isinstance(effect, DoWhile):
        return DoWhile(_rewrite_goto(effect.body, label), effect.cond)
    if isinstance(effect, ForC):
        return ForC(
            effect.name,
            effect.type,
            _rewrite_goto(effect.init, label),
            effect.guard,
            _rewrite_goto(effect.step, label),
            _rewrite_goto(effect.body, label),
        )
    if isinstance(effect, ForRange):
        return ForRange(effect.name, effect.type, effect.iterable, _rewrite_goto(effect.body, label))
    if isinstance(effect, Iterator):
        return Iterator(effect.name, effect.type, effect.iterable, _rewrite_goto(effect.body, label))
    if isinstance(effect, Let):
        return Let(effect.name, effect.type, _rewrite_goto(effect.value, label), _rewrite_goto(effect.body, label))
    if isinstance(effect, Quantified):
        return Quantified(effect.quantifier, effect.name, effect.type, effect.domain, _rewrite_goto(effect.body, label))
    return effect


def eliminate_gotos(effect: EffectExpr) -> EffectExpr:
    """Lower sequential forward labels to labeled blocks.

    ``…; goto L; …; L: epilogue`` → ``'L: { …; break 'L; … } epilogue``.

    The labeled statement's epilogue (statements after the label) is moved after
    the block; ``break 'L`` exits the block to it. Re-applied to the epilogue so
    multiple sequential labels work.
    """
    if not isinstance(effect, Sequence):
        return effect

    items = list(effect.items)
    label_idx: int | None = None
    label_name: str | None = None
    for i, it in enumerate(items):
        name = _is_label(it)
        if name is not None:
            label_idx, label_name = i, name
            break
    if label_idx is None:
        return effect

    before = tuple(_rewrite_goto(it, label_name) for it in items[:label_idx])
    epilogue = tuple(items[label_idx + 1 :])
    block = LabeledBlock(label_name, Sequence(before))

    tail = eliminate_gotos(Sequence(epilogue))
    tail_items = tail.items if isinstance(tail, Sequence) else (tail,)
    return Sequence((block, *tail_items))
