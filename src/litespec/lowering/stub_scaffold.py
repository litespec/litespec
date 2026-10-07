"""Stub scaffold generation for external symbols (Phase 4).

Real C functions reference macros, helper functions, typedefs, and constants
that have no Rust definition after lowering. This module collects those symbols
from a LIR effect and emits a compiling prelude: unknown types become opaque
``usize`` handles, unknown functions become ``unsafe fn … { unimplemented!() }``
stubs (returning ``bool`` when used as predicates, ``usize`` when used as
values), and unknown free variables become ``const …: usize = 0;`` stubs.
"""

from __future__ import annotations

from litespec.lir.effect_expr_ast import (
    Assign,
    BinOp,
    Call,
    CallEffect,
    Compare,
    Conditional,
    DoWhile,
    EffectExpr,
    Expr,
    ExprStmt,
    Field,
    ForC,
    ForRange,
    Guard,
    Index,
    Iterator,
    LabeledBlock,
    Let,
    Not,
    Quantified,
    Return,
    Sequence,
    Ternary,
    Var,
    While,
)
from litespec.lowering.effect_expr_to_rust import assigned_targets
from litespec.lowering.rust_type_mapping import int_type, rust_type

_RUST_PRIMITIVES = {
    "usize",
    "isize",
    "u8",
    "u16",
    "u32",
    "u64",
    "i8",
    "i16",
    "i32",
    "i64",
    "f64",
    "bool",
    "String",
    "()",
}
_CONTROL = {"__break__", "__continue__"}


def _walk_expr(
    expr: Expr,
    referenced: set[str],
    arity: dict[str, set[int]],
    predicates: set[str],
    value_calls: set[str],
    bool_ctx: bool = False,
) -> None:
    if isinstance(expr, Var):
        # Field/index projections (``a.b``, ``a[i]``) are memory accesses through
        # handles, not standalone constants; skip them here.
        if expr.name not in _CONTROL and "." not in expr.name and "[" not in expr.name:
            referenced.add(expr.name)
    elif isinstance(expr, Call):
        arity.setdefault(expr.name, set()).add(len(expr.args))
        if bool_ctx:
            predicates.add(expr.name)
        else:
            value_calls.add(expr.name)
        for a in expr.args:
            _walk_expr(a, referenced, arity, predicates, value_calls, False)
    elif isinstance(expr, Compare):
        _walk_expr(expr.left, referenced, arity, predicates, value_calls, False)
        _walk_expr(expr.right, referenced, arity, predicates, value_calls, False)
    elif isinstance(expr, Field):
        _walk_expr(expr.base, referenced, arity, predicates, value_calls, False)
        value_calls.add(f"field_{expr.name}")
        arity.setdefault(f"field_{expr.name}", set()).add(1)
    elif isinstance(expr, Index):
        _walk_expr(expr.base, referenced, arity, predicates, value_calls, False)
        _walk_expr(expr.index, referenced, arity, predicates, value_calls, False)
        value_calls.add("get")
        arity.setdefault("get", set()).add(2)
    elif isinstance(expr, Ternary):
        _walk_expr(expr.cond, referenced, arity, predicates, value_calls, True)
        _walk_expr(expr.then, referenced, arity, predicates, value_calls, False)
        _walk_expr(expr.else_, referenced, arity, predicates, value_calls, False)
    elif isinstance(expr, BinOp):
        logical = expr.op in ("and", "or")
        _walk_expr(expr.left, referenced, arity, predicates, value_calls, logical)
        _walk_expr(expr.right, referenced, arity, predicates, value_calls, logical)
    elif isinstance(expr, Not):
        _walk_expr(expr.operand, referenced, arity, predicates, value_calls, True)


def _walk_effect(
    effect: EffectExpr,
    referenced: set[str],
    arity: dict[str, set[int]],
    predicates: set[str],
    value_calls: set[str],
) -> None:
    if isinstance(effect, Assign) or isinstance(effect, ExprStmt):
        _walk_expr(effect.expr, referenced, arity, predicates, value_calls)
    elif isinstance(effect, CallEffect):
        arity.setdefault(effect.name, set()).add(len(effect.args))
        for a in effect.args:
            _walk_expr(a, referenced, arity, predicates, value_calls)
    elif isinstance(effect, Conditional):
        _walk_expr(effect.cond, referenced, arity, predicates, value_calls, True)
        _walk_effect(effect.then, referenced, arity, predicates, value_calls)
        _walk_effect(effect.else_, referenced, arity, predicates, value_calls)
    elif isinstance(effect, (While, DoWhile)):
        _walk_expr(effect.cond, referenced, arity, predicates, value_calls, True)
        _walk_effect(effect.body, referenced, arity, predicates, value_calls)
    elif isinstance(effect, (ForRange, Iterator)):
        _walk_expr(effect.iterable, referenced, arity, predicates, value_calls)
        _walk_effect(effect.body, referenced, arity, predicates, value_calls)
    elif isinstance(effect, ForC):
        _walk_effect(effect.init, referenced, arity, predicates, value_calls)
        _walk_expr(effect.guard, referenced, arity, predicates, value_calls, True)
        _walk_effect(effect.step, referenced, arity, predicates, value_calls)
        _walk_effect(effect.body, referenced, arity, predicates, value_calls)
    elif isinstance(effect, Let):
        _walk_effect(effect.value, referenced, arity, predicates, value_calls)
        _walk_effect(effect.body, referenced, arity, predicates, value_calls)
    elif isinstance(effect, Quantified) or isinstance(effect, LabeledBlock):
        _walk_effect(effect.body, referenced, arity, predicates, value_calls)
    elif isinstance(effect, Return) and effect.expr is not None:
        _walk_expr(effect.expr, referenced, arity, predicates, value_calls)
    elif isinstance(effect, Guard):
        _walk_expr(effect.cond, referenced, arity, predicates, value_calls, True)
    elif isinstance(effect, Sequence):
        for item in effect.items:
            _walk_effect(item, referenced, arity, predicates, value_calls)


def collect_external_symbols(
    effect: EffectExpr,
    params: list[tuple[str, str]],
    state_vars: list[tuple[str, str]],
    return_type: str,
) -> tuple[set[str], dict[str, tuple[int, str, bool]], set[str], set[str]]:
    """Return ``(unknown_types, functions{name: (arity, rust_return, variadic)}, constants, fn_ptrs)``.

    ``fn_ptrs`` are names both *called* and *referenced as a value* — i.e. C
    function-pointer variables/weak symbols (``if (Hook != NULL) Hook(...)``), which
    must be globals, not function stubs.
    """
    declared = {n for n, _ in params} | {n for n, _ in state_vars} | assigned_targets(effect)
    referenced: set[str] = set()
    arity: dict[str, set[int]] = {}
    predicates: set[str] = set()
    value_calls: set[str] = set()
    _walk_effect(effect, referenced, arity, predicates, value_calls)

    fn_ptrs = set(arity) & referenced
    constants = referenced - declared - set(arity)

    functions: dict[str, tuple[int, str, bool]] = {}
    for name, arities in arity.items():
        # C predicates return an integer; conditions test ``!= 0``.
        rt = int_type() if (name in predicates or name in value_calls) else "()"
        functions[name] = (max(arities), rt, len(arities) > 1)

    unknown_types: set[str] = set()
    for _, t in params + state_vars + [(None, return_type)]:
        rt = rust_type(t)
        if rt == t and t not in _RUST_PRIMITIVES:
            unknown_types.add(t)

    return unknown_types, functions, constants, fn_ptrs


#: Stub names rendered as deterministic bump-allocator calls (retiring per-test
#: allocator ``mock_returns``); maps name → Rust body using ``_aN`` arg references.
BUMP_ALLOCATORS = {
    "LOS_MemAlloc": "__mem_alloc(_a1)",  # (pool, size) → alloc size words
    "LOS_MemAllocAlign": "__mem_alloc_align(_a1, _a2)",  # (pool, size, align)
}


def render_stub_scaffold(
    unknown_types: set[str],
    functions: dict[str, tuple[int, str, bool]],
    constants: set[str],
    executable: bool = False,
    mock_returns: dict[str, int] | None = None,
) -> str:
    """Render a compiling prelude for the collected external symbols.

    With ``executable=True``, ``usize``-returning stubs return ``0`` (and ``()`` stubs
    do nothing) instead of ``unimplemented!()``, so the emitted module can actually run.
    ``mock_returns`` overrides a stub's return value (e.g. a mock allocator address).
    ``BUMP_ALLOCATORS`` stubs render as deterministic bump-allocator calls instead of a
    fixed value, retiring per-test allocator mocks.
    """
    lines: list[str] = []
    for t in sorted(unknown_types):
        lines.append(f"type {t} = {int_type()};")
    for name in sorted(functions):
        n_args, rt, variadic = functions[name]
        if variadic:
            # called with inconsistent arity (e.g. PRINT_ERR / OsHookCall) → macro stub
            lines.append(f"macro_rules! {name} {{ ($($a:tt)*) => {{ }} }}")
        else:
            args = ", ".join(f"_a{i}: {int_type()}" for i in range(n_args))
            if name in BUMP_ALLOCATORS:
                body = BUMP_ALLOCATORS[name]
            elif mock_returns and name in mock_returns:
                body = str(mock_returns[name])
            else:
                body = "0" if (executable and rt == int_type()) else "unimplemented!()"
            lines.append(f"unsafe fn {name}({args}) -> {rt} {{ {body} }}")
    for c in sorted(constants):
        lines.append(f"const {c}: {int_type()} = 0;")
    return "\n".join(lines)
