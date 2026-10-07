"""Frozen ``EffectExpr`` AST (§7.5).

The AST is immutable (frozen dataclasses). It carries the ``fv``, ``bound``, and
``substitute`` scope-model operations directly, per §7.5.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# --------------------------------------------------------------------------- #
# Expressions (§7.5: BoolExpr | ArithmeticExpr)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Expr:
    """Base expression node."""

    def identifiers(self) -> set[str]:
        raise NotImplementedError


@dataclass(frozen=True)
class BoolLit(Expr):
    value: bool

    def identifiers(self) -> set[str]:
        return set()


@dataclass(frozen=True)
class IntLit(Expr):
    value: int

    def identifiers(self) -> set[str]:
        return set()


@dataclass(frozen=True)
class Var(Expr):
    name: str

    def identifiers(self) -> set[str]:
        return {self.name}


@dataclass(frozen=True)
class Call(Expr):
    name: str
    args: tuple[Expr, ...] = ()

    def identifiers(self) -> set[str]:
        ids = {self.name}
        for a in self.args:
            ids |= a.identifiers()
        return ids


@dataclass(frozen=True)
class BinOp(Expr):
    op: str  # + - * / and or implies
    left: Expr
    right: Expr

    def identifiers(self) -> set[str]:
        return self.left.identifiers() | self.right.identifiers()


@dataclass(frozen=True)
class Not(Expr):
    operand: Expr

    def identifiers(self) -> set[str]:
        return self.operand.identifiers()


@dataclass(frozen=True)
class Compare(Expr):
    op: str  # < <= > >= = !=
    left: Expr
    right: Expr

    def identifiers(self) -> set[str]:
        return self.left.identifiers() | self.right.identifiers()


@dataclass(frozen=True)
class Field(Expr):
    """Struct field projection: ``base.name`` (pointer → index handle)."""

    base: Expr
    name: str

    def identifiers(self) -> set[str]:
        return self.base.identifiers()


@dataclass(frozen=True)
class Deref(Expr):
    """Pointer dereference: ``*ptr`` → the value at the address ``ptr``."""

    ptr: Expr

    def identifiers(self) -> set[str]:
        return self.ptr.identifiers()


@dataclass(frozen=True)
class AddrOf(Expr):
    """Address-of: ``&x`` → the address of ``x`` (a handle/index)."""

    target: Expr

    def identifiers(self) -> set[str]:
        return self.target.identifiers()


@dataclass(frozen=True)
class Ternary(Expr):
    """Conditional expression: ``cond ? then : else_``."""

    cond: Expr
    then: Expr
    else_: Expr

    def identifiers(self) -> set[str]:
        return self.cond.identifiers() | self.then.identifiers() | self.else_.identifiers()


@dataclass(frozen=True)
class Index(Expr):
    """Array subscript: ``base[index]``."""

    base: Expr
    index: Expr

    def identifiers(self) -> set[str]:
        return self.base.identifiers() | self.index.identifiers()


# --------------------------------------------------------------------------- #
# Effect expressions (§7.5)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class EffectExpr:
    """Base effect-expression node."""

    def fv(self, ctx: Optional[dict[str, str]] = None) -> set[str]:
        raise NotImplementedError

    def bound(self, ctx: Optional[dict[str, str]] = None) -> set[str]:
        raise NotImplementedError

    def substitute(self, x: str, e: Expr, ctx: Optional[dict[str, str]] = None) -> EffectExpr:
        raise NotImplementedError

    def clone_effect_tree(self) -> EffectExpr:
        """Deep, structure-preserving copy (binders retain their type annotations)."""
        return self


@dataclass(frozen=True)
class ExprStmt(EffectExpr):
    """A bare expression evaluated for effect (SimpleExpr)."""

    expr: Expr

    def fv(self, ctx=None):
        return self.expr.identifiers()

    def bound(self, ctx=None):
        return set()

    def substitute(self, x, e, ctx=None):
        return ExprStmt(subst_expr(self.expr, x, e))


@dataclass(frozen=True)
class Assign(EffectExpr):
    target: Expr  # Var (local) | Field | Index (memory write)
    expr: Expr

    def __post_init__(self):
        # backward-compat: a bare string target is a local variable
        if isinstance(self.target, str):
            object.__setattr__(self, "target", Var(self.target))

    def fv(self, ctx=None):
        return self.expr.identifiers() | self.target.identifiers()

    def bound(self, ctx=None):
        return set()

    def substitute(self, x, e, ctx=None):
        return Assign(subst_expr(self.target, x, e), subst_expr(self.expr, x, e))


@dataclass(frozen=True)
class SetUpdate(EffectExpr):
    target: str
    source: str
    removed: Expr
    added: Expr

    def fv(self, ctx=None):
        return {self.target, self.source} | self.removed.identifiers() | self.added.identifiers()

    def bound(self, ctx=None):
        return set()

    def substitute(self, x, e, ctx=None):
        return SetUpdate(
            self.target,
            self.source,
            subst_expr(self.removed, x, e),
            subst_expr(self.added, x, e),
        )


@dataclass(frozen=True)
class Skip(EffectExpr):
    def fv(self, ctx=None):
        return set()

    def bound(self, ctx=None):
        return set()

    def substitute(self, x, e, ctx=None):
        return self


@dataclass(frozen=True)
class Conditional(EffectExpr):
    cond: Expr
    then: EffectExpr
    else_: EffectExpr

    def fv(self, ctx=None):
        return self.cond.identifiers() | self.then.fv(ctx) | self.else_.fv(ctx)

    def bound(self, ctx=None):
        return self.then.bound(ctx) | self.else_.bound(ctx)

    def substitute(self, x, e, ctx=None):
        return Conditional(
            subst_expr(self.cond, x, e),
            self.then.substitute(x, e, ctx),
            self.else_.substitute(x, e, ctx),
        )


@dataclass(frozen=True)
class Let(EffectExpr):
    name: str
    type: str
    value: EffectExpr
    body: EffectExpr

    def fv(self, ctx=None):
        return self.value.fv(ctx) | (self.body.fv(ctx) - {self.name})

    def bound(self, ctx=None):
        return {self.name} | self.body.bound(ctx)

    def substitute(self, x, e, ctx=None):
        if x == self.name:
            return Let(self.name, self.type, self.value.substitute(x, e, ctx), self.body)
        if self.name in e.identifiers():
            fresh = fresh_rename(self.name, e.identifiers() | self.body.fv(ctx) | self.body.bound(ctx) | {x})
            renamed = rename_var(self.body, self.name, fresh)
            return Let(fresh, self.type, self.value.substitute(x, e, ctx), renamed.substitute(x, e, ctx))
        return Let(self.name, self.type, self.value.substitute(x, e, ctx), self.body.substitute(x, e, ctx))


@dataclass(frozen=True)
class Quantified(EffectExpr):
    quantifier: str  # "exists" | "forall"
    name: str
    type: str
    domain: str
    body: EffectExpr

    def fv(self, ctx=None):
        return _domain_identifiers(self.domain) | (self.body.fv(ctx) - {self.name})

    def bound(self, ctx=None):
        return {self.name} | self.body.bound(ctx)

    def substitute(self, x, e, ctx=None):
        if x == self.name:
            return Quantified(self.quantifier, self.name, self.type, self.domain, self.body)
        if self.name in e.identifiers():
            fresh = fresh_rename(self.name, e.identifiers() | self.body.fv(ctx) | self.body.bound(ctx) | {x})
            renamed = rename_var(self.body, self.name, fresh)
            return Quantified(self.quantifier, fresh, self.type, self.domain, renamed.substitute(x, e, ctx))
        return Quantified(self.quantifier, self.name, self.type, self.domain, self.body.substitute(x, e, ctx))


@dataclass(frozen=True)
class Sequence(EffectExpr):
    items: tuple[EffectExpr, ...] = ()

    def fv(self, ctx=None):
        out: set[str] = set()
        for it in self.items:
            out |= it.fv(ctx)
        return out

    def bound(self, ctx=None):
        out: set[str] = set()
        for it in self.items:
            out |= it.bound(ctx)
        return out

    def substitute(self, x, e, ctx=None):
        return Sequence(tuple(it.substitute(x, e, ctx) for it in self.items))


@dataclass(frozen=True)
class While(EffectExpr):
    cond: Expr
    body: EffectExpr

    def fv(self, ctx=None):
        return self.cond.identifiers() | self.body.fv(ctx)

    def bound(self, ctx=None):
        return self.body.bound(ctx)

    def substitute(self, x, e, ctx=None):
        return While(subst_expr(self.cond, x, e), self.body.substitute(x, e, ctx))


@dataclass(frozen=True)
class ForRange(EffectExpr):
    name: str
    type: str
    iterable: Expr
    body: EffectExpr

    def fv(self, ctx=None):
        return self.iterable.identifiers() | (self.body.fv(ctx) - {self.name})

    def bound(self, ctx=None):
        return {self.name} | self.body.bound(ctx)

    def substitute(self, x, e, ctx=None):
        if x == self.name:
            return ForRange(self.name, self.type, subst_expr(self.iterable, x, e), self.body)
        if self.name in e.identifiers():
            fresh = fresh_rename(self.name, e.identifiers() | self.body.fv(ctx) | self.body.bound(ctx) | {x})
            renamed = rename_var(self.body, self.name, fresh)
            return ForRange(fresh, self.type, subst_expr(self.iterable, x, e), renamed.substitute(x, e, ctx))
        return ForRange(self.name, self.type, subst_expr(self.iterable, x, e), self.body.substitute(x, e, ctx))


@dataclass(frozen=True)
class ForC(EffectExpr):
    name: str
    type: str
    init: EffectExpr
    guard: Expr
    step: EffectExpr
    body: EffectExpr

    def fv(self, ctx=None):
        inner = (self.guard.identifiers() | self.step.fv(ctx) | self.body.fv(ctx)) - {self.name}
        return self.init.fv(ctx) | inner

    def bound(self, ctx=None):
        return {self.name} | self.init.bound(ctx) | self.guard_bound() | self.step.bound(ctx) | self.body.bound(ctx)

    def guard_bound(self) -> set[str]:
        return set()

    def substitute(self, x, e, ctx=None):
        if x == self.name:
            return ForC(self.name, self.type, self.init.substitute(x, e, ctx), self.guard, self.step, self.body)
        if self.name in e.identifiers():
            fresh = fresh_rename(
                self.name,
                e.identifiers()
                | self.init.fv(ctx)
                | self.guard.identifiers()
                | self.step.fv(ctx)
                | self.body.fv(ctx)
                | self.init.bound(ctx)
                | self.step.bound(ctx)
                | self.body.bound(ctx)
                | {x},
            )
            return ForC(
                fresh,
                self.type,
                self.init.substitute(x, e, ctx),
                subst_expr(rename_expr(self.guard, self.name, fresh), x, e),
                rename_var(self.step, self.name, fresh).substitute(x, e, ctx),
                rename_var(self.body, self.name, fresh).substitute(x, e, ctx),
            )
        return ForC(
            self.name,
            self.type,
            self.init.substitute(x, e, ctx),
            subst_expr(self.guard, x, e),
            self.step.substitute(x, e, ctx),
            self.body.substitute(x, e, ctx),
        )


@dataclass(frozen=True)
class DoWhile(EffectExpr):
    body: EffectExpr
    cond: Expr

    def fv(self, ctx=None):
        return self.body.fv(ctx) | self.cond.identifiers()

    def bound(self, ctx=None):
        return self.body.bound(ctx)

    def substitute(self, x, e, ctx=None):
        return DoWhile(self.body.substitute(x, e, ctx), subst_expr(self.cond, x, e))


@dataclass(frozen=True)
class BreakLabel(EffectExpr):
    """``break 'label`` — exits a labeled block (forward-goto lowering)."""

    name: str

    def fv(self, ctx=None):
        return set()

    def bound(self, ctx=None):
        return set()

    def substitute(self, x, e, ctx=None):
        return self


@dataclass(frozen=True)
class LabeledBlock(EffectExpr):
    """``'name: { body }`` — a Rust labeled block (forward-goto lowering)."""

    name: str
    body: EffectExpr

    def fv(self, ctx=None):
        return self.body.fv(ctx)

    def bound(self, ctx=None):
        return self.body.bound(ctx)

    def substitute(self, x, e, ctx=None):
        return LabeledBlock(self.name, self.body.substitute(x, e, ctx))


@dataclass(frozen=True)
class Iterator(EffectExpr):
    name: str
    type: str
    iterable: Expr
    body: EffectExpr

    def fv(self, ctx=None):
        return self.iterable.identifiers() | (self.body.fv(ctx) - {self.name})

    def bound(self, ctx=None):
        return {self.name} | self.body.bound(ctx)

    def substitute(self, x, e, ctx=None):
        if x == self.name:
            return Iterator(self.name, self.type, subst_expr(self.iterable, x, e), self.body)
        if self.name in e.identifiers():
            fresh = fresh_rename(self.name, e.identifiers() | self.body.fv(ctx) | self.body.bound(ctx) | {x})
            renamed = rename_var(self.body, self.name, fresh)
            return Iterator(fresh, self.type, subst_expr(self.iterable, x, e), renamed.substitute(x, e, ctx))
        return Iterator(self.name, self.type, subst_expr(self.iterable, x, e), self.body.substitute(x, e, ctx))


@dataclass(frozen=True)
class CallEffect(EffectExpr):
    name: str
    args: tuple[Expr, ...] = ()

    def fv(self, ctx=None):
        ids = {self.name}
        for a in self.args:
            ids |= a.identifiers()
        return ids

    def bound(self, ctx=None):
        return set()

    def substitute(self, x, e, ctx=None):
        return CallEffect(self.name, tuple(subst_expr(a, x, e) for a in self.args))


@dataclass(frozen=True)
class Guard(EffectExpr):
    cond: Expr

    def fv(self, ctx=None):
        return self.cond.identifiers()

    def bound(self, ctx=None):
        return set()

    def substitute(self, x, e, ctx=None):
        return Guard(subst_expr(self.cond, x, e))


@dataclass(frozen=True)
class Return(EffectExpr):
    expr: Optional[Expr] = None

    def fv(self, ctx=None):
        return self.expr.identifiers() if self.expr is not None else set()

    def bound(self, ctx=None):
        return set()

    def substitute(self, x, e, ctx=None):
        return Return(subst_expr(self.expr, x, e) if self.expr is not None else None)


# --------------------------------------------------------------------------- #
# expression helpers
# --------------------------------------------------------------------------- #


def subst_expr(expr: Expr, x: str, e: Expr) -> Expr:
    """Capture-avoiding substitution at the expression level (no binders here)."""
    if isinstance(expr, Var):
        return e if expr.name == x else expr
    if isinstance(expr, (BoolLit, IntLit)):
        return expr
    if isinstance(expr, Call):
        return Call(expr.name, tuple(subst_expr(a, x, e) for a in expr.args))
    if isinstance(expr, BinOp):
        return BinOp(expr.op, subst_expr(expr.left, x, e), subst_expr(expr.right, x, e))
    if isinstance(expr, Not):
        return Not(subst_expr(expr.operand, x, e))
    if isinstance(expr, Compare):
        return Compare(expr.op, subst_expr(expr.left, x, e), subst_expr(expr.right, x, e))
    if isinstance(expr, Field):
        return Field(subst_expr(expr.base, x, e), expr.name)
    if isinstance(expr, Index):
        return Index(subst_expr(expr.base, x, e), subst_expr(expr.index, x, e))
    if isinstance(expr, Deref):
        return Deref(subst_expr(expr.ptr, x, e))
    if isinstance(expr, AddrOf):
        return AddrOf(subst_expr(expr.target, x, e))
    if isinstance(expr, Ternary):
        return Ternary(subst_expr(expr.cond, x, e), subst_expr(expr.then, x, e), subst_expr(expr.else_, x, e))
    return expr


def rename_expr(expr: Expr, old: str, new: str) -> Expr:
    """Rename free occurrences of ``old`` to ``new`` in an expression."""
    return subst_expr(expr, old, Var(new))


def rename_var(effect: EffectExpr, old: str, new: str) -> EffectExpr:
    """Rename free occurrences of ``old`` to ``new`` in an effect expression."""
    return effect.substitute(old, Var(new), None)


def fresh_rename(name: str, forbidden: set[str]) -> str:
    """Return ``name'``, ``name''``, ... avoiding the forbidden set."""
    candidate = name
    while candidate in forbidden:
        candidate += "'"
    return candidate


def _domain_identifiers(domain: str) -> set[str]:
    """Collect identifier tokens from a binder-domain string (best-effort)."""
    import re

    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", domain))


def render_expr(expr: Expr) -> str:
    """Render an ``Expr`` back to its canonical string form (§7.5)."""
    if isinstance(expr, BoolLit):
        return "true" if expr.value else "false"
    if isinstance(expr, IntLit):
        return str(expr.value)
    if isinstance(expr, Var):
        return expr.name
    if isinstance(expr, Call):
        return f"{expr.name}({', '.join(render_expr(a) for a in expr.args)})"
    if isinstance(expr, Not):
        return f"not {render_expr(expr.operand)}"
    if isinstance(expr, Compare):
        return f"{render_expr(expr.left)} {expr.op} {render_expr(expr.right)}"
    if isinstance(expr, BinOp):
        return f"{render_expr(expr.left)} {expr.op} {render_expr(expr.right)}"
    if isinstance(expr, Field):
        return f"{render_expr(expr.base)}.{expr.name}"
    if isinstance(expr, Index):
        return f"{render_expr(expr.base)}[{render_expr(expr.index)}]"
    if isinstance(expr, Ternary):
        return f"({render_expr(expr.cond)} ? {render_expr(expr.then)} : {render_expr(expr.else_)})"
    return str(expr)
