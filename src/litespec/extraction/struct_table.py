"""Struct definition extraction from a translation unit (Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from tree_sitter import Node

from litespec.extraction.expression_mapping import _text

_TYPE_NODES = {
    "primitive_type",
    "type_identifier",
    "sized_type_specifier",
    "type_descriptor",
    "struct_specifier",
    "enum_specifier",
    "union_specifier",
}


@dataclass(frozen=True)
class StructField:
    name: str
    base_type: str  # C type text (e.g. "unsigned int", "struct OsMemNodeHead")
    is_pointer: bool = False
    array_size: int | None = None
    is_array: bool = False


@dataclass
class StructTable:
    """``name → tuple[StructField, …]`` for structs defined in a translation unit."""

    structs: dict[str, tuple[StructField, ...]] = field(default_factory=dict)
    #: Field names that are members of an anonymous ``union { … }`` — they overlap
    #: at the union's offset (e.g. ``node->ptr.prev``/``node->ptr.next``).
    union_members: set[str] = field(default_factory=set)

    @classmethod
    def from_translation_unit(cls, tu: Node) -> StructTable:
        from litespec.extraction.macro_table import MacroTable

        table = cls()
        macros = MacroTable.from_translation_unit(tu)

        def walk(node: Node) -> None:
            if node.type == "struct_specifier":
                tag: str | None = None
                body: Node | None = None
                for c in node.named_children:
                    if c.type == "type_identifier" and tag is None:
                        tag = _text(c)
                    elif c.type == "field_declaration_list":
                        body = c
                if tag is not None and body is not None:
                    fields, union = _parse_fields(body, macros)
                    table.structs[tag] = fields
                    table.union_members |= union
            elif node.type == "type_definition":
                # ``typedef struct { … } Name;`` — anonymous struct: the typedef
                # name is the sibling ``type_identifier`` (not a struct tag).
                struct_node: Node | None = None
                name: str | None = None
                for c in node.named_children:
                    if c.type in ("struct_specifier", "union_specifier"):
                        struct_node = c
                    elif c.type == "type_identifier" and name is None:
                        name = _text(c)
                if struct_node is not None and name is not None:
                    body = next((c for c in struct_node.named_children if c.type == "field_declaration_list"), None)
                    if body is not None:
                        fields, union = _parse_fields(body, macros)
                        table.structs.setdefault(name, fields)
                        table.union_members |= union
            for c in node.named_children:
                walk(c)

        walk(tu)
        return table

    def is_empty(self) -> bool:
        return not self.structs

    def field_offsets(self, sizes: dict[str, int] | None = None) -> dict[str, int]:
        """Field name → word offset (first occurrence wins), cumulative across fields.

        Uses word counts (via ``sizes``) so an embedded sub-struct advances the offset
        by its own word count. If ``sizes`` is not given, it is computed from this table.
        """
        if sizes is None:
            from litespec.extraction.size_table import compute_sizes

            sizes = compute_sizes(self)

        def words(field: StructField) -> int:
            if field.is_pointer:
                elem = 1  # a pointer is one word, regardless of pointed-to size
            else:
                base = field.base_type.replace("struct ", "").replace("enum ", "").replace("union ", "").strip()
                elem = sizes.get(base, 1)
            return (field.array_size or 1) * elem

        offsets: dict[str, int] = {}
        for fields in self.structs.values():
            running = 0
            for f in fields:
                # Last occurrence wins: later structs (typically the module's own,
                # defined after the shared kernel headers they include) take
                # precedence over earlier, unrelated structs that reuse a name.
                offsets[f.name] = running
                running += words(f)
        return offsets

    def scoped_field_offsets(self, sizes: dict[str, int] | None = None) -> dict[str, int]:
        """``struct.field`` → word offset (struct-scoped; no cross-struct name collisions)."""
        if sizes is None:
            from litespec.extraction.size_table import compute_sizes

            sizes = compute_sizes(self)

        def words(field: StructField) -> int:
            if field.is_pointer:
                elem = 1
            else:
                base = field.base_type.replace("struct ", "").replace("enum ", "").replace("union ", "").strip()
                elem = sizes.get(base, 1)
            return (field.array_size or 1) * elem

        offsets: dict[str, int] = {}
        for sname, fields in self.structs.items():
            running = 0
            for f in fields:
                offsets[f"{sname}.{f.name}"] = running
                running += words(f)
        return offsets

    def field_types(self) -> dict[str, str]:
        """``struct.field`` → field's base type name (pointer/embedded target, for nesting)."""
        out: dict[str, str] = {}
        for sname, fields in self.structs.items():
            for f in fields:
                base = f.base_type.replace("struct ", "").replace("enum ", "").replace("union ", "").strip()
                out[f"{sname}.{f.name}"] = base
        return out

    def field_elem_sizes(self, sizes: dict[str, int] | None = None) -> dict[str, int]:
        """Array field name → element word size (for ``offsetof(type, field[i])``)."""
        if sizes is None:
            from litespec.extraction.size_table import compute_sizes

            sizes = compute_sizes(self)

        out: dict[str, int] = {}
        for fields in self.structs.values():
            for f in fields:
                if f.is_array:
                    base = f.base_type.replace("struct ", "").replace("enum ", "").replace("union ", "").strip()
                    elem = 1 if f.is_pointer else sizes.get(base, 1)
                    out.setdefault(f.name, elem)
        return out

    def embedded_fields(self) -> set[str]:
        """Field names whose access yields an *address* (embedded struct/union, or array decay)."""
        return {
            f.name
            for fields in self.structs.values()
            for f in fields
            if f.is_array or (not f.is_pointer and f.base_type.strip().startswith(("struct ", "enum ", "union ")))
        }


def _find_array_declarator(node: Node) -> Node | None:
    if node.type == "array_declarator":
        return node
    for c in node.named_children:
        r = _find_array_declarator(c)
        if r is not None:
            return r
    return None


def _parse_fields(body: Node, macros=None) -> tuple[tuple[StructField, ...], set[str]]:
    fields: list[StructField] = []
    union_members: set[str] = set()
    for fd in body.named_children:
        if fd.type != "field_declaration":
            continue
        base_type = ""
        declarators: list[Node] = []
        for c in fd.named_children:
            if c.type in _TYPE_NODES:
                base_type = _text(c)
            else:
                declarators.append(c)
        base_type = base_type or "unsigned int"
        # Record members of an anonymous ``union { … }`` (they overlap at the union's offset).
        union_members |= _union_member_names(fd)
        for d in declarators:
            name = _field_name(d)
            if not name:
                continue
            arr = _find_array_declarator(d)  # handles `*ptr[N]` (pointer-to-array)
            fields.append(
                StructField(
                    name=name,
                    base_type=base_type,
                    is_pointer=d.type == "pointer_declarator",
                    array_size=_array_size(arr, macros) if arr is not None else None,
                    is_array=arr is not None,
                )
            )
    return tuple(fields), union_members


def _union_member_names(fd: Node) -> set[str]:
    """Names of fields inside an anonymous ``union { … }`` in a field declaration."""
    names: set[str] = set()
    for c in fd.named_children:
        if c.type != "union_specifier":
            continue
        body = next((x for x in c.named_children if x.type == "field_declaration_list"), None)
        if body is None:
            continue
        for inner in body.named_children:
            if inner.type != "field_declaration":
                continue
            for d in inner.named_children:
                if d.type in _TYPE_NODES:
                    continue
                name = _field_name(d)
                if name:
                    names.add(name)
    return names


def _field_name(node: Node) -> str:
    if node.type in ("field_identifier", "identifier"):
        return _text(node)
    for c in node.named_children:
        r = _field_name(c)
        if r:
            return r
    return ""


def _eval_const(expr) -> int | None:
    """Fold a resolved LIR expression to a constant int (for array sizes)."""
    from litespec.lir.effect_expr_ast import BinOp, IntLit

    if isinstance(expr, IntLit):
        return expr.value
    if isinstance(expr, BinOp):
        l = _eval_const(expr.left)
        r = _eval_const(expr.right)
        if l is None or r is None:
            return None
        return {
            "+": l + r,
            "-": l - r,
            "*": l * r,
            "/": l // r,
            "%": l % r,
            "<<": l << r,
            ">>": l >> r,
            "&": l & r,
            "|": l | r,
            "^": l ^ r,
        }.get(expr.op)
    return None


def _array_size(node: Node, macros=None) -> int | None:
    for c in node.named_children:
        if c.type == "number_literal":
            try:
                return int(_text(c), 0)
            except ValueError:
                return None
    if macros is not None:
        from litespec.extraction.macro_resolution import _expr_from_text, _resolve_expr

        for c in node.named_children:
            if c.type in ("identifier", "binary_expression", "parenthesized_expression"):
                expr = _resolve_expr(_expr_from_text(_text(c)), macros, 0)
                val = _eval_const(expr)
                if val is not None:
                    return val
    return None
