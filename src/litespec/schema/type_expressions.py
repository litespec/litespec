"""Type expressions (§7.2) and type declarations (§7.2 / §14.1)."""

from __future__ import annotations

import re
from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.primitives import Identifier

# §7.2 primitive type names.
PRIMITIVE_TYPES = frozenset(
    {
        "Bool",
        "Nat",
        "Int",
        "Rat",
        "String",
        "PowerState",
        "GPUState",
        "ServiceState",
        "TimerQueue",
        "WakeupSource",
        "WakeupSourceSet",
    }
)

_TYPE_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class TypeExpr(LiteSpecModel):
    """A structured type expression (§7.2 grammar).

    ``TypeExpr ::= primitive | Identifier | List<TypeExpr> | Set<TypeExpr>
    | Map<TypeExpr, TypeExpr> | RecordType``.
    """

    kind: str  # "primitive" | "identifier" | "list" | "set" | "map" | "record"
    name: Optional[str] = None
    element: Optional[TypeExpr] = None
    key: Optional[TypeExpr] = None
    value: Optional[TypeExpr] = None
    fields: Optional[dict[str, TypeExpr]] = None

    def is_identifier(self) -> bool:
        return self.kind == "identifier"

    def is_primitive(self) -> bool:
        return self.kind == "primitive"


class TypeDeclaration(LiteSpecModel):
    """§7.2 ``TypeDeclaration ::= { name, definition }``."""

    name: Identifier
    definition: str

    def parsed_definition(self) -> TypeExpr:
        return parse_type_expr(self.definition)


def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i].isspace():
        i += 1
    return i


def _parse_type(s: str, i: int) -> tuple[TypeExpr, int]:
    i = _skip_ws(s, i)
    if i < len(s) and s[i] == "{":
        # record type
        i += 1
        fields: dict[str, TypeExpr] = {}
        while True:
            i = _skip_ws(s, i)
            m = _TYPE_RE.match(s, i)
            if not m:
                raise ValueError(f"expected field name in record type at index {i}: {s!r}")
            fname = m.group(0)
            i = _skip_ws(s, m.end())
            if i >= len(s) or s[i] != ":":
                raise ValueError(f"expected ':' after field {fname!r} at index {i}")
            i += 1
            ftype, i = _parse_type(s, i)
            fields[fname] = ftype
            i = _skip_ws(s, i)
            if i < len(s) and s[i] == ",":
                i += 1
                continue
            if i < len(s) and s[i] == "}":
                i += 1
                break
            raise ValueError(f"expected ',' or '}}' in record type at index {i}: {s!r}")
        return TypeExpr(kind="record", fields=fields), i

    m = _TYPE_RE.match(s, i)
    if not m:
        raise ValueError(f"expected type at index {i}: {s!r}")
    head = m.group(0)
    i = _skip_ws(s, m.end())
    if i < len(s) and s[i] == "<":
        i += 1
        first, i = _parse_type(s, i)
        i = _skip_ws(s, i)
        if head == "Map":
            if i >= len(s) or s[i] != ",":
                raise ValueError(f"expected ',' in Map<...> at index {i}: {s!r}")
            i += 1
            second, i = _parse_type(s, i)
            i = _skip_ws(s, i)
            if i >= len(s) or s[i] != ">":
                raise ValueError(f"expected '>' in Map<...> at index {i}: {s!r}")
            i += 1
            return TypeExpr(kind="map", key=first, value=second), i
        if head not in ("List", "Set"):
            raise ValueError(f"unknown parameterised type {head!r}")
        if i >= len(s) or s[i] != ">":
            raise ValueError(f"expected '>' in {head}<...> at index {i}: {s!r}")
        i += 1
        return TypeExpr(kind=head.lower(), element=first), i

    if head in PRIMITIVE_TYPES:
        return TypeExpr(kind="primitive", name=head), i
    return TypeExpr(kind="identifier", name=head), i


def parse_type_expr(text: str) -> TypeExpr:
    """Parse a §7.2 type-expression string into a structured ``TypeExpr``."""
    if text is None:
        raise ValueError("type expression is None")
    expr, i = _parse_type(text, 0)
    i = _skip_ws(text, i)
    if i != len(text):
        raise ValueError(f"trailing characters in type expression at index {i}: {text!r}")
    return expr


def format_type_expr(expr: TypeExpr) -> str:
    """Render a structured ``TypeExpr`` back to its canonical string form."""
    if expr.kind == "record":
        return "{" + ", ".join(f"{k}: {format_type_expr(v)}" for k, v in (expr.fields or {}).items()) + "}"
    if expr.kind in ("list", "set"):
        return f"{'List' if expr.kind == 'list' else 'Set'}<{format_type_expr(expr.element)}>"
    if expr.kind == "map":
        return f"Map<{format_type_expr(expr.key)}, {format_type_expr(expr.value)}>"
    return expr.name or ""
