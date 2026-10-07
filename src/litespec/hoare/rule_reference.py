"""Hoare rule mapping (§7.5c) and premise synthesis (§9.21.4)."""

from __future__ import annotations

from litespec.lir.effect_expr_ast import (
    Assign,
    CallEffect,
    Conditional,
    DoWhile,
    EffectExpr,
    ExprStmt,
    ForC,
    ForRange,
    Guard,
    Iterator,
    Let,
    Quantified,
    Return,
    Sequence,
    SetUpdate,
    Skip,
    While,
)


def rule_of_command(effect: EffectExpr) -> str:
    """Map an ``EffectExpr`` constructor to its ``HoareRuleKind`` (Rule 7.5c)."""
    if isinstance(effect, (Assign, SetUpdate)):
        return "assign"
    if isinstance(effect, Skip):
        return "skip"
    if isinstance(effect, Conditional):
        return "if"
    if isinstance(effect, Let):
        return "let"
    if isinstance(effect, Quantified):
        return "quant_forall" if effect.quantifier == "forall" else "quant_exists_finite"
    if isinstance(effect, Sequence):
        return "seq"
    if isinstance(effect, (While, ForRange, ForC, DoWhile, Iterator)):
        return "while"
    if isinstance(effect, CallEffect):
        return "call"
    if isinstance(effect, Guard):
        return "skip"
    if isinstance(effect, Return):
        return "return"
    if isinstance(effect, ExprStmt):
        # A bare expression statement (e.g. a ForC init ``0``) is an assignment.
        return "assign"
    return "skip"


def is_compound_rule(rule: str) -> bool:
    """Whether a rule recursively decomposes into sub-parts."""
    return rule in {"seq", "if", "while", "let", "quant_forall", "quant_exists_finite"}
