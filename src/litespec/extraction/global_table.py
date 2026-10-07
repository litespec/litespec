"""File-scope (global) variable extraction (Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from tree_sitter import Node

from litespec.extraction.expression_mapping import _child, _find_identifier, _text

_DECL_NODES = {
    "primitive_type",
    "type_identifier",
    "sized_type_specifier",
    "type_descriptor",
    "struct_specifier",
    "enum_specifier",
    "union_specifier",
}

_QUALIFIERS = {"STATIC", "INLINE", "EXTERN", "VOID", "CONST", "VOLATILE"}


def _is_function_declarator(node: Node | None) -> bool:
    """True if a declarator (or any descendant) is a function declarator."""
    if node is None:
        return False
    if node.type == "function_declarator":
        return True
    return any(_is_function_declarator(c) for c in node.named_children)


@dataclass
class GlobalTable:
    """Names of file-scope (static/global) variables in a translation unit."""

    names: set[str] = field(default_factory=set)

    @classmethod
    def from_translation_unit(cls, tu: Node) -> GlobalTable:
        names: set[str] = set()

        def walk(node: Node) -> None:
            if node.type == "function_definition":
                return  # do not descend into function bodies
            if node.type == "declaration":
                for d in node.named_children:
                    declarator = None
                    if d.type == "init_declarator":
                        declarator = _child(d, "declarator")
                    elif d.type in ("array_declarator", "pointer_declarator", "identifier", "field_identifier"):
                        # ``extern Type name;`` / ``extern Type name[N];`` — the
                        # declarator is a direct child (no init_declarator wrapper).
                        declarator = d
                    if declarator is None or _is_function_declarator(declarator):
                        continue
                    name = _find_identifier(declarator)
                    if name is not None and _text(name) not in _QUALIFIERS:
                        names.add(_text(name))
            for child in node.named_children:
                walk(child)

        walk(tu)
        return cls(names=names)

    def __contains__(self, name: str) -> bool:
        return name in self.names
