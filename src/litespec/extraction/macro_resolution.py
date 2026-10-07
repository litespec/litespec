"""Macro resolution: expand ``#define`` macros in an extracted LIR effect (Phase 2)."""

from __future__ import annotations

import re

from litespec.extraction.c_parser import parse_c
from litespec.extraction.expression_mapping import _fold_const, map_expression
from litespec.extraction.macro_table import MacroTable
from litespec.lir.effect_expr_ast import (
    AddrOf,
    Assign,
    BinOp,
    Call,
    CallEffect,
    Compare,
    Conditional,
    Deref,
    DoWhile,
    EffectExpr,
    Expr,
    ExprStmt,
    Field,
    ForC,
    ForRange,
    Guard,
    Index,
    IntLit,
    Iterator,
    LabeledBlock,
    Let,
    Not,
    Quantified,
    Return,
    Sequence,
    SetUpdate,
    Ternary,
    Var,
    While,
    subst_expr,
)

_MAX_DEPTH = 48

_EXPR_TYPES = {
    "number_literal",
    "identifier",
    "binary_expression",
    "parenthesized_expression",
    "unary_expression",
    "call_expression",
    "field_expression",
    "subscript_expression",
    "cast_expression",
    "conditional_expression",
    "string_literal",
    "sizeof_expression",
    "update_expression",
    "true",
    "false",
    "null",
}


def _find_expr(node) -> Expr | None:
    if node.type in _EXPR_TYPES:
        return node
    for child in node.named_children:
        found = _find_expr(child)
        if found is not None:
            return found
    return None


def _expr_from_text(text: str) -> Expr:
    """Parse a C expression text into a LIR ``Expr``."""
    tu = parse_c(text.encode())
    node = _find_expr(tu)
    if node is not None:
        return map_expression(node)
    # tree-sitter parses ``(foo())`` as a parenthesized *type* (ERROR), not a call;
    # retry with outer parentheses stripped so the inner call is seen as an expression.
    stripped = text.strip()
    while stripped.startswith("(") and stripped.endswith(")"):
        stripped = stripped[1:-1].strip()
        node = _find_expr(parse_c(stripped.encode()))
        if node is not None:
            return map_expression(node)
    # Unparseable (statement-expression, inline asm, …) → opaque atom, never a
    # raw-text Var (which would emit an invalid Rust identifier as a const stub).
    return Var("__litespec_opaque")


def _resolve_expr(expr: Expr, macros: MacroTable, depth: int) -> Expr:
    if depth > _MAX_DEPTH:
        return expr

    if isinstance(expr, Var):
        if expr.name in macros.constants:
            value = macros.constants[expr.name]
            return _resolve_expr(_expr_from_text(value), macros, depth + 1)
        return expr

    if isinstance(expr, Call):
        if expr.name in ("LOS_OFF_SET_OF", "offsetof") and len(expr.args) == 2:
            # offsetof(type, member) → the member's word offset (container_of support)
            member = expr.args[1]
            if isinstance(member, Var):
                from litespec.extraction.expression_mapping import _FIELD_OFFSETS, _SCOPED_OFFSETS

                type_name = expr.args[0].name if isinstance(expr.args[0], Var) else ""
                if type_name:
                    return IntLit(_SCOPED_OFFSETS.get(f"{type_name}.{member.name}", _FIELD_OFFSETS.get(member.name, 0)))
                return IntLit(_FIELD_OFFSETS.get(member.name, 0))
            if isinstance(member, Index) and isinstance(member.base, Var):
                from litespec.extraction.expression_mapping import _FIELD_ELEM_SIZES, _FIELD_OFFSETS, _SCOPED_OFFSETS

                type_name = expr.args[0].name if isinstance(expr.args[0], Var) else ""
                key = f"{type_name}.{member.base.name}" if type_name else member.base.name
                base = _SCOPED_OFFSETS.get(key, _FIELD_OFFSETS.get(member.base.name, 0))
                idx = member.index.value if isinstance(member.index, IntLit) else 0
                return IntLit(base + idx * _FIELD_ELEM_SIZES.get(member.base.name, 1))
            return IntLit(0)
        if expr.name == "LOS_Align" and len(expr.args) == 2:
            # LOS_Align(addr, boundary) = (addr + boundary - 1) & ~(boundary - 1); pure.
            a = _resolve_expr(expr.args[0], macros, depth + 1)
            b = _resolve_expr(expr.args[1], macros, depth + 1)
            if isinstance(a, IntLit) and isinstance(b, IntLit) and b.value > 0:
                return IntLit((a.value + b.value - 1) & ~(b.value - 1))
            return Call(expr.name, (a, b))
        if expr.name in macros.functions:
            params, body = macros.functions[expr.name]
            expanded = _expr_from_text(body)
            for p, a in zip(params, expr.args):
                expanded = subst_expr(expanded, p, a)
            return _resolve_expr(expanded, macros, depth + 1)
        return Call(expr.name, tuple(_resolve_expr(a, macros, depth + 1) for a in expr.args))

    if isinstance(expr, BinOp):
        left = _resolve_expr(expr.left, macros, depth + 1)
        right = _resolve_expr(expr.right, macros, depth + 1)
        if isinstance(left, IntLit) and isinstance(right, IntLit):
            folded = _fold_const(expr.op, left.value, right.value)
            if folded is not None:
                return IntLit(folded)
        return BinOp(expr.op, left, right)
    if isinstance(expr, Compare):
        return Compare(
            expr.op, _resolve_expr(expr.left, macros, depth + 1), _resolve_expr(expr.right, macros, depth + 1)
        )
    if isinstance(expr, Not):
        return Not(_resolve_expr(expr.operand, macros, depth + 1))
    if isinstance(expr, Field):
        return Field(_resolve_expr(expr.base, macros, depth + 1), expr.name)
    if isinstance(expr, Index):
        return Index(_resolve_expr(expr.base, macros, depth + 1), _resolve_expr(expr.index, macros, depth + 1))
    if isinstance(expr, Deref):
        return Deref(_resolve_expr(expr.ptr, macros, depth + 1))
    if isinstance(expr, AddrOf):
        return AddrOf(_resolve_expr(expr.target, macros, depth + 1))
    if isinstance(expr, Ternary):
        return Ternary(
            _resolve_expr(expr.cond, macros, depth + 1),
            _resolve_expr(expr.then, macros, depth + 1),
            _resolve_expr(expr.else_, macros, depth + 1),
        )
    return expr


def _expr_to_c_text(expr: Expr) -> str:
    """Reverse-render a LIR ``Expr`` back to C source text (for macro substitution)."""
    if isinstance(expr, Var):
        return expr.name
    if isinstance(expr, Field):
        return f"{_expr_to_c_text(expr.base)}->{expr.name}"
    if isinstance(expr, Index):
        return f"{_expr_to_c_text(expr.base)}[{_expr_to_c_text(expr.index)}]"
    if isinstance(expr, Deref):
        return f"*({_expr_to_c_text(expr.ptr)})"
    if isinstance(expr, AddrOf):
        return f"&({_expr_to_c_text(expr.target)})"
    if isinstance(expr, IntLit):
        return str(expr.value)
    if isinstance(expr, BinOp):
        return f"({_expr_to_c_text(expr.left)} {expr.op} {_expr_to_c_text(expr.right)})"
    if isinstance(expr, Call):
        return f"{expr.name}({', '.join(_expr_to_c_text(a) for a in expr.args)})"
    return str(expr)


def _find_assignment(node) -> object | None:
    """Find the first ``assignment_expression`` node, or ``None``."""
    if node.type == "assignment_expression":
        return node
    for c in node.named_children:
        found = _find_assignment(c)
        if found is not None:
            return found
    return None


def _expand_assignment_macro(call: Call, macros: MacroTable, depth: int) -> EffectExpr:
    """Expand a statement-macro (body is an assignment) to an ``Assign`` effect."""
    from litespec.extraction.statement_mapping import _map_step

    params, body = macros.functions[call.name]
    text = body
    for p, a in zip(params, call.args):
        text = re.sub(r"\b" + re.escape(p) + r"\b", lambda _m, a=a: _expr_to_c_text(a), text)
    node = _find_assignment(parse_c(text.encode()))
    if node is None:
        return ExprStmt(call)
    assign = _map_step(node)
    return Assign(
        _resolve_expr(assign.target, macros, depth + 1),
        _resolve_expr(assign.expr, macros, depth + 1),
    )


def _find_for(node):
    """Find the first ``for_statement`` node (for a for-loop statement-macro body)."""
    if node.type == "for_statement":
        return node
    for child in node.named_children:
        found = _find_for(child)
        if found is not None:
            return found
    return None


def _resolve_effect(effect: EffectExpr, macros: MacroTable, depth: int) -> EffectExpr:
    if depth > _MAX_DEPTH:
        return effect

    if isinstance(effect, Assign):
        return Assign(_resolve_expr(effect.target, macros, depth + 1), _resolve_expr(effect.expr, macros, depth + 1))
    if isinstance(effect, ExprStmt):
        # A statement-macro (e.g. ``OS_MEM_NODE_SET_USED_FLAG(x)``) expands to an
        # assignment ``(x) = (x | FLAG)``; expand it as an Assign, not a value.
        if isinstance(effect.expr, Call) and effect.expr.name in macros.functions:
            _, body = macros.functions[effect.expr.name]
            if _find_assignment(parse_c(body.encode())) is not None:
                return _expand_assignment_macro(effect.expr, macros, depth)
        return ExprStmt(_resolve_expr(effect.expr, macros, depth + 1))
    if isinstance(effect, SetUpdate):
        return SetUpdate(
            effect.target,
            effect.source,
            _resolve_expr(effect.removed, macros, depth + 1),
            _resolve_expr(effect.added, macros, depth + 1),
        )
    if isinstance(effect, Sequence):
        return Sequence(tuple(_resolve_effect(i, macros, depth + 1) for i in effect.items))
    if isinstance(effect, Conditional):
        return Conditional(
            _resolve_expr(effect.cond, macros, depth + 1),
            _resolve_effect(effect.then, macros, depth + 1),
            _resolve_effect(effect.else_, macros, depth + 1),
        )
    if isinstance(effect, While):
        return While(_resolve_expr(effect.cond, macros, depth + 1), _resolve_effect(effect.body, macros, depth + 1))
    if isinstance(effect, DoWhile):
        return DoWhile(_resolve_effect(effect.body, macros, depth + 1), _resolve_expr(effect.cond, macros, depth + 1))
    if isinstance(effect, ForC):
        return ForC(
            effect.name,
            effect.type,
            _resolve_effect(effect.init, macros, depth + 1),
            _resolve_expr(effect.guard, macros, depth + 1),
            _resolve_effect(effect.step, macros, depth + 1),
            _resolve_effect(effect.body, macros, depth + 1),
        )
    if isinstance(effect, ForRange):
        return ForRange(
            effect.name,
            effect.type,
            _resolve_expr(effect.iterable, macros, depth + 1),
            _resolve_effect(effect.body, macros, depth + 1),
        )
    if isinstance(effect, Iterator):
        return Iterator(
            effect.name,
            effect.type,
            _resolve_expr(effect.iterable, macros, depth + 1),
            _resolve_effect(effect.body, macros, depth + 1),
        )
    if isinstance(effect, Let):
        return Let(
            effect.name,
            effect.type,
            _resolve_effect(effect.value, macros, depth + 1),
            _resolve_effect(effect.body, macros, depth + 1),
        )
    if isinstance(effect, Quantified):
        return Quantified(
            effect.quantifier, effect.name, effect.type, effect.domain, _resolve_effect(effect.body, macros, depth + 1)
        )
    if isinstance(effect, Return):
        return Return(_resolve_expr(effect.expr, macros, depth + 1) if effect.expr is not None else None)
    if isinstance(effect, Guard):
        return Guard(_resolve_expr(effect.cond, macros, depth + 1))
    if isinstance(effect, CallEffect):
        return CallEffect(effect.name, tuple(_resolve_expr(a, macros, depth + 1) for a in effect.args))
    if isinstance(effect, LabeledBlock):
        return LabeledBlock(effect.name, _resolve_effect(effect.body, macros, depth + 1))
    return effect


def resolve_macros(effect: EffectExpr, macros: MacroTable) -> EffectExpr:
    """Expand object-like and function-like macros in an extracted effect."""
    if macros.is_empty():
        return effect
    return _resolve_effect(effect, macros, 0)
