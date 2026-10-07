"""ISIR emission (interscope.md §5): build a ``.isir`` module from LIR constructs."""

from __future__ import annotations

from typing import Any

import yaml

from litespec.lir.effect_expr_ast import (
    Assign,
    BinOp,
    BoolLit,
    Call,
    Compare,
    Conditional,
    DoWhile,
    EffectExpr,
    Expr,
    ExprStmt,
    Field,
    ForC,
    ForRange,
    Index,
    IntLit,
    Iterator,
    Let,
    Not,
    Quantified,
    Return,
    Sequence,
    Skip,
    Ternary,
    Var,
    While,
)
from litespec.schema.contract_layer import ContractLayer
from litespec.type_mapping import default_type_model

_OP_SYMS = {
    "+": "add",
    "-": "sub",
    "*": "mul",
    "/": "div",
    "%": "mod",
    "and": "and",
    "or": "or",
    "implies": "implies",
    "<": "lt",
    "<=": "le",
    ">": "gt",
    ">=": "ge",
    "=": "eq",
    "!=": "neq",
}


def isir_type(type_expr: str) -> str:
    """Map a LIR ``TypeExpr`` to an ISIR type string (via the configured type model)."""
    return default_type_model().lir_to_isir_type(type_expr.strip())


def render_isir_expr(expr: Expr) -> str:
    """Render a LIR ``Expr`` as an ISIR S-expression."""
    if isinstance(expr, BoolLit):
        return "true" if expr.value else "false"
    if isinstance(expr, IntLit):
        return str(expr.value)
    if isinstance(expr, Var):
        return f"(read {expr.name})"
    if isinstance(expr, Call):
        return f"({expr.name} {' '.join(render_isir_expr(a) for a in expr.args)})"
    if isinstance(expr, Not):
        return f"(not {render_isir_expr(expr.operand)})"
    if isinstance(expr, Compare):
        op = _OP_SYMS.get(expr.op, expr.op)
        return f"({op} {render_isir_expr(expr.left)} {render_isir_expr(expr.right)})"
    if isinstance(expr, BinOp):
        op = _OP_SYMS.get(expr.op, expr.op)
        return f"({op} {render_isir_expr(expr.left)} {render_isir_expr(expr.right)})"
    if isinstance(expr, Field):
        return f"(field {render_isir_expr(expr.base)} {expr.name})"
    if isinstance(expr, Index):
        return f"(select {render_isir_expr(expr.base)} {render_isir_expr(expr.index)})"
    if isinstance(expr, Ternary):
        return f"(ite {render_isir_expr(expr.cond)} {render_isir_expr(expr.then)} {render_isir_expr(expr.else_)})"
    return str(expr)


def render_isir_lvalue(expr: Expr) -> str:
    """Render an assignment target as an ISIR write location."""
    if isinstance(expr, Var):
        return expr.name
    return render_isir_expr(expr)  # Field/Index → (field …)/(select …)


def effect_to_actions(effect: EffectExpr) -> list[str]:
    """Flatten an ``EffectExpr`` into ISIR rule actions (``write`` S-expressions)."""
    actions: list[str] = []

    def walk(e: EffectExpr) -> None:
        if isinstance(e, Assign):
            actions.append(f"(write {render_isir_lvalue(e.target)} {render_isir_expr(e.expr)})")
        elif isinstance(e, Sequence):
            for item in e.items:
                walk(item)
        elif isinstance(e, ExprStmt):
            actions.append(render_isir_expr(e.expr))
        elif isinstance(e, Conditional):
            walk(e.then)
            walk(e.else_)
        elif isinstance(e, (While, ForRange, Iterator, DoWhile)):
            walk(e.body)
        elif isinstance(e, ForC):
            walk(e.init)
            walk(e.step)
            walk(e.body)
        elif isinstance(e, Let):
            walk(e.value)
            walk(e.body)
        elif isinstance(e, Quantified):
            walk(e.body)
        elif isinstance(e, (Skip, Return)):
            pass
        else:
            actions.append(str(e))

    walk(effect)
    return actions


def build_clocks_resets() -> tuple[list[dict], list[dict]]:
    clocks = [{"name": "clk", "edge": "posedge"}]
    resets = [{"name": "rst", "polarity": "active_high", "async": False, "affects": "all"}]
    return clocks, resets


def build_state(state_vars: list[tuple[str, str]]) -> list[dict]:
    return [{"name": name, "kind": "register", "type": isir_type(typ), "initial": 0} for name, typ in state_vars]


def build_inputs(params: list[tuple[str, str]]) -> list[dict]:
    return [{"name": name, "direction": "input", "type": isir_type(typ)} for name, typ in params]


def build_rules(function: str, effect: EffectExpr) -> list[dict]:
    return [{"name": function, "action": effect_to_actions(effect)}]


def build_directives(contract: ContractLayer) -> list[dict]:
    return [
        {"type": "assume", "name": f"pre_{i}", "expression": p.expression} for i, p in enumerate(contract.preconditions)
    ]


def build_properties(contract: ContractLayer) -> list[dict]:
    return [
        {"name": f"post_{i}", "kind": "safety", "expression": {"kind": "always", "operand": p.expression}}
        for i, p in enumerate(contract.postconditions)
    ]


def build_proof_obligations(contract: ContractLayer, backend: str = "acl2") -> list[dict]:
    """Emit proof obligations for the postconditions.

    ``backend`` is the InterScope prover target (``koika``/``acl2``/``model_checking``).
    ``model_checking`` is an *engine* (not a ``backend`` — the schema's ``backend``
    enum is only ``koika|kōika|acl2``), so it is emitted as ``engine: model_checking``
    with no ``backend`` field. ``acl2`` is the default (binary + acl2-mcp + mcp all
    available locally); ``koika`` needs the OCaml/Coq toolchain, ``model_checking``
    needs SymbiYosys.
    """
    if backend == "model_checking":
        return [
            {"property": f"post_{i}", "status": "unproved", "engine": "model_checking"}
            for i in range(len(contract.postconditions))
        ]
    return [
        {"property": f"post_{i}", "status": "unproved", "engine": "theorem_proving", "backend": backend}
        for i in range(len(contract.postconditions))
    ]


def emit_isir_module(
    name: str,
    state_vars: list[tuple[str, str]],
    effect: EffectExpr,
    contract: ContractLayer | None = None,
    params: list[tuple[str, str]] | None = None,
    backend: str = "acl2",
) -> dict[str, Any]:
    """Build an ISIR module dict from LIR state vars, an effect, and a contract.

    ``backend`` selects the InterScope prover target for the emitted proof
    obligations (``koika``/``acl2``/``model_checking``).
    """
    contract = contract or ContractLayer()
    clocks, resets = build_clocks_resets()
    module: dict[str, Any] = {
        "name": name,
        "clocks": clocks,
        "resets": resets,
        "state": build_state(state_vars),
        "rules": build_rules(name, effect),
    }
    if params:
        module["inputs"] = build_inputs(params)
    # Emit the LIR→ISIR abstraction relation α (Phase 3 → Phase 7): the α map
    # expression + its signal scope, so the lir_to_isir seam can check coherence.
    from litespec.abstraction import derive_abstraction_relation, synthesize_signal_scope

    signals = synthesize_signal_scope(state_vars)
    relation = derive_abstraction_relation(state_vars, signals)
    module["abstraction"] = {"relation": relation.model_dump(), "signals": signals}

    # Emit the ConcAbsDialect (rely-guarantee) when the effect carries concurrency
    # constructs (atomics / spin-lock / per-CPU) — Phase 10.
    from litespec.interscope.dialects import derive_conc_abs_dialect

    conc = derive_conc_abs_dialect(effect)
    if conc.atomic_actions or conc.context != "atomic" or conc.threads != ["cpu_0"]:
        module["conc_abstraction"] = conc.model_dump()

    directives = build_directives(contract)
    properties = build_properties(contract)
    obligations = build_proof_obligations(contract, backend=backend)
    if directives:
        module["directives"] = directives
    if properties:
        module["properties"] = properties
    if obligations:
        module["proof_obligations"] = obligations
    return {"isir_version": "0.1", "module": module}


def dumps_isir(isir: dict[str, Any]) -> str:
    """Serialize an ISIR module to ``.isir`` YAML text."""
    return yaml.safe_dump(isir, sort_keys=False, allow_unicode=True)
