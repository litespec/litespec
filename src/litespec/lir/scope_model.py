"""LIR scope model (§7.5.1): ``fv``, ``bound``, ``substitute``, ``typing_context_at``."""

from __future__ import annotations

from typing import Optional

from litespec.lir.effect_expr_ast import EffectExpr, Expr, fresh_rename

TypingContext = Optional[dict[str, str]]


def fv(effect: EffectExpr, ctx: TypingContext = None) -> set[str]:
    """Free variables of ``effect`` (parameterised by optional typing context)."""
    return effect.fv(ctx)


def bound(effect: EffectExpr, ctx: TypingContext = None) -> set[str]:
    """Bound variables of ``effect``."""
    return effect.bound(ctx)


def substitute(effect: EffectExpr, x: str, e: Expr, ctx: TypingContext = None) -> EffectExpr:
    """Capture-avoiding, typed substitution (§7.5.1)."""
    return effect.substitute(x, e, ctx)


def type_of(x: str, ctx: TypingContext) -> Optional[str]:
    """§7.5.1 type lookup: ``Γ[x]`` or ``⊥``."""
    if ctx is None:
        return None
    return ctx.get(x)


def enclosing_binders_of(d) -> list:
    """Collect every binder in the syntactic ancestor chain of ``d``.

    Phase 1 (D67): the ancestor chain is reconstructed from the decomposition's
    ``parent_triple`` / sub-part nesting. Phase 0 returns the empty chain.
    """
    return []


def typing_context_at(d) -> dict[str, str]:
    """§7.5.1 ``typing_context_at(d)``: binders of the enclosing scope mapped to types."""
    return {b.name: b.type for b in enclosing_binders_of(d) if getattr(b, "name", None)}


__all__ = [
    "TypingContext",
    "bound",
    "enclosing_binders_of",
    "fresh_rename",
    "fv",
    "substitute",
    "type_of",
    "typing_context_at",
]
