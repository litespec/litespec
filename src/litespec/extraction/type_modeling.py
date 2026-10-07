"""C type → LIR ``TypeExpr`` modeling (Phase 2).

C→LIR type decisions are delegated to the configured type model
(``config/type-models/<name>.yaml``); this module only extracts the type text
from tree-sitter and detects pointer declarators.
"""

from __future__ import annotations

from typing import Optional

from tree_sitter import Node

from litespec.type_mapping import TypeModel, default_type_model


def _tm(type_model: Optional[TypeModel]) -> TypeModel:
    return type_model or default_type_model()


def primitive_type_text(node: Optional[Node]) -> str:
    """Normalized text of a C type node (whitespace collapsed)."""
    if node is None:
        return ""
    return b" ".join(node.text.split()).decode()


def c_type_to_type_expr(
    type_node: Optional[Node], *, pointer: bool = False, type_model: Optional[TypeModel] = None
) -> str:
    """Map a C type node (+ pointer flag) to a §7.2 ``TypeExpr`` string."""
    text = primitive_type_text(type_node)
    return _tm(type_model).c_type_to_lir(text, pointer=pointer)


def c_param_to_type_expr(raw_text: str, name: str, type_model: Optional[TypeModel] = None) -> str:
    """Map a C parameter declaration text (e.g. ``unsigned int size``) to a TypeExpr."""
    type_text = raw_text
    if name:
        # strip the trailing parameter name (it may also appear inside the type,
        # e.g. the 'n' in "unsigned"); the name is always the last identifier.
        idx = raw_text.rfind(name)
        if idx != -1:
            type_text = (raw_text[:idx] + raw_text[idx + len(name) :]).strip()
    pointer = "*" in type_text
    return _tm(type_model).c_type_to_lir(type_text, pointer=pointer)


def c_return_to_type_expr(raw_text: str, type_model: Optional[TypeModel] = None) -> str:
    """Map a C return-type text (e.g. ``void *``) to a TypeExpr."""
    pointer = "*" in raw_text
    return _tm(type_model).c_type_to_lir(raw_text, pointer=pointer)


def declaration_type(
    type_node: Optional[Node], declarator: Optional[Node], type_model: Optional[TypeModel] = None
) -> str:
    """Type of a declaration, accounting for pointer declarators."""
    pointer = declarator is not None and b"*" in (declarator.text or b"")
    return c_type_to_type_expr(type_node, pointer=pointer, type_model=type_model)
