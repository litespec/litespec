"""D85 ``DeriveTypeDeclarations`` (§13)."""

from __future__ import annotations

from litespec.schema.type_declarations import PRIMITIVE_TYPES, TypeDeclaration, TypeExpr, parse_type_expr


def _identifier_types(expr: TypeExpr) -> set[str]:
    if expr.kind == "identifier":
        return {expr.name or ""}
    if expr.kind in ("list", "set"):
        return _identifier_types(expr.element) if expr.element else set()
    if expr.kind == "map":
        out: set[str] = set()
        if expr.key:
            out |= _identifier_types(expr.key)
        if expr.value:
            out |= _identifier_types(expr.value)
        return out
    if expr.kind == "record":
        out = set()
        for v in (expr.fields or {}).values():
            out |= _identifier_types(v)
        return out
    return set()


def collect_identifier_type_exprs(state_vars: list[tuple[str, str]]) -> set[str]:
    """Collect user-defined identifier-typed ``TypeExpr`` names (non-primitives)."""
    ids: set[str] = set()
    for _name, type_str in state_vars:
        try:
            expr = parse_type_expr(type_str)
        except ValueError:
            continue
        ids |= _identifier_types(expr)
    return {i for i in ids if i and i not in PRIMITIVE_TYPES and i != "Unit"}


def derive_type_declarations(
    state_vars: list[tuple[str, str]], existing: set[str] | None = None
) -> list[TypeDeclaration]:
    """D85: register a ``TypeDeclaration`` for every unresolved identifier type."""
    already = set(existing or ())
    return [
        TypeDeclaration(name=name, definition="Unit")
        for name in sorted(collect_identifier_type_exprs(state_vars))
        if name not in already
    ]
