"""Top-level C→LIR extraction (Phase 2): parse C, select a function, map to LIR."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from tree_sitter import Node

from litespec.extraction.c_parser import parse_c
from litespec.extraction.c_translation_unit import CFunction, find_function
from litespec.extraction.expression_mapping import (
    _child,
    _find_identifier,
    _text,
    set_field_elem_sizes,
    set_field_offsets,
    set_ptr_sizes,
    set_scoped_field_offsets,
    set_sizes,
)
from litespec.extraction.macro_resolution import resolve_macros
from litespec.extraction.macro_table import MacroTable
from litespec.extraction.statement_mapping import map_function_body
from litespec.extraction.type_modeling import declaration_type
from litespec.lir.effect_expr_ast import EffectExpr
from litespec.type_mapping import TypeModel, default_type_model


@dataclass
class ExtractedFunction:
    name: str
    return_type: str
    parameters: list[tuple[str, str]]
    effect: EffectExpr
    state_vars: list[tuple[str, str]]  # local variables: (name, TypeExpr)


def _type_node(declaration: Node) -> Node | None:
    for child in declaration.named_children:
        if child.type in ("primitive_type", "type_identifier", "sized_type_specifier", "type_descriptor"):
            return child
        if child.type in ("struct_specifier", "enum_specifier", "union_specifier"):
            # Use the tag name (``struct S`` → ``S``; a ``type_identifier`` child).
            for tag in child.named_children:
                if tag.type == "type_identifier":
                    return tag
            return child  # anonymous struct: fall back to the whole specifier
    return None


_TYPE_DECL_NODES = {
    "primitive_type",
    "type_identifier",
    "sized_type_specifier",
    "type_descriptor",
    "struct_specifier",
    "enum_specifier",
    "union_specifier",
}


def _collect_local_vars(body: Node, type_model: TypeModel) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def walk(node: Node) -> None:
        for child in node.named_children:
            if child.type == "declaration":
                type_node = _type_node(child)
                for d in child.named_children:
                    if d.type in _TYPE_DECL_NODES:
                        continue  # the type specifier(s)
                    declarator = _child(d, "declarator") if d.type == "init_declarator" else d
                    name = _find_identifier(declarator)
                    if name is not None and _text(name) not in seen:
                        seen.add(_text(name))
                        out.append((_text(name), declaration_type(type_node, declarator, type_model=type_model)))
            else:
                walk(child)  # recurse into if/while/for/#if blocks too

    walk(body)
    return out


def _struct_ptr_sizes(body: Node, sizes: dict[str, int]) -> dict[str, int]:
    """Local/param name → word size of the pointed-to struct (for C pointer arithmetic)."""
    out: dict[str, int] = {}

    def walk(node: Node) -> None:
        for child in node.named_children:
            if child.type == "declaration":
                struct_name: str | None = None
                for c in child.named_children:
                    if c.type == "struct_specifier":
                        for tag in c.named_children:
                            if tag.type == "type_identifier":
                                struct_name = _text(tag)
                                break
                    elif c.type == "type_identifier":
                        # typedef'd struct pointer (e.g. ``LosTaskCB *p``)
                        struct_name = _text(c)
                if struct_name is not None and struct_name in sizes:
                    w = sizes.get(struct_name, 1)
                    for d in child.named_children:
                        if d.type in _TYPE_DECL_NODES:
                            continue
                        declarator = _child(d, "declarator") if d.type == "init_declarator" else d
                        if declarator is not None and declarator.type in ("pointer_declarator", "array_declarator"):
                            name = _find_identifier(declarator)
                            if name is not None:
                                out[_text(name)] = w
            else:
                walk(child)

    walk(body)
    return out


def _global_struct_ptr_sizes(tu: Node, sizes: dict[str, int]) -> dict[str, int]:
    """File-scope (global) struct-pointer name → word size of the pointed-to struct."""
    out: dict[str, int] = {}

    def walk(node: Node) -> None:
        if node.type == "function_definition":
            return  # globals only
        if node.type == "declaration":
            struct_name: str | None = None
            for c in node.named_children:
                if c.type == "type_identifier":
                    struct_name = _text(c)
                    break
            if struct_name is not None and struct_name in sizes:
                for d in node.named_children:
                    if d.type in _TYPE_DECL_NODES or d.type == "type_identifier":
                        continue
                    declarator = _child(d, "declarator") if d.type == "init_declarator" else d
                    # struct pointer OR array-of-struct (``g_schedRunqueue[i]`` scales by sizeof)
                    if declarator is not None and declarator.type in ("pointer_declarator", "array_declarator"):
                        name = _find_identifier(declarator)
                        if name is not None:
                            out[_text(name)] = sizes[struct_name]
        for child in node.named_children:
            walk(child)

    walk(tu)
    return out


def extract_function(
    c_source: Union[str, bytes], name: str, type_model: TypeModel | None = None, config=None
) -> ExtractedFunction:
    """Extract a single C function to LIR (EffectExpr + state vars + signature)."""
    tm = type_model or default_type_model()
    tu = parse_c(c_source)
    fn: CFunction | None = find_function(tu, name)
    if fn is None:
        raise ValueError(f"function {name!r} not found in translation unit")

    from litespec.extraction.size_table import compute_sizes
    from litespec.extraction.struct_table import StructTable

    struct_table = StructTable.from_translation_unit(tu)
    sizes = compute_sizes(struct_table)
    set_sizes(sizes)
    set_ptr_sizes({**_global_struct_ptr_sizes(tu, sizes), **_struct_ptr_sizes(fn.body, sizes)})
    set_field_offsets(struct_table.field_offsets(sizes))
    set_scoped_field_offsets(struct_table.scoped_field_offsets(sizes))
    set_field_elem_sizes(struct_table.field_elem_sizes(sizes))

    macros = MacroTable.from_translation_unit(tu)
    # Seed config defines (LOSCFG_* values from the target's preprocess section) so
    # macro references like ``LOSCFG_KERNEL_SMP_CORE_NUM`` resolve to their values.
    from litespec.targets.loader import load_target

    for k, v in load_target("liteos").preprocess_defines.items():
        macros.constants.setdefault(k, str(v))
    from litespec.extraction.statement_mapping import set_macros

    set_macros(macros)
    effect = map_function_body(fn.body, config)
    state_vars = _collect_local_vars(fn.body, tm) if fn.body is not None else []
    effect = resolve_macros(effect, macros)
    return ExtractedFunction(
        name=fn.name,
        return_type=fn.return_type,
        parameters=fn.parameters,
        effect=effect,
        state_vars=state_vars,
    )
