"""C translation unit and function selection (Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tree_sitter import Node

from litespec.extraction.expression_mapping import _find_identifier, _text


@dataclass
class CFunction:
    name: str
    return_type: str
    parameters: list[tuple[str, str]]  # (name, type text)
    body: Optional[Node]  # compound_statement


def _function_name(fn_def: Node) -> str:
    for child in fn_def.named_children:
        if child.type in ("function_declarator", "pointer_declarator"):
            ident = _find_identifier(child)
            if ident is not None:
                return _text(ident)
    return ""


def _function_declarator(fn_def: Node) -> Optional[Node]:
    for child in fn_def.named_children:
        if child.type in ("function_declarator", "pointer_declarator"):
            return child
    return None


def _find_descendant(node: Node, type_name: str) -> Optional[Node]:
    if node.type == type_name:
        return node
    for child in node.named_children:
        found = _find_descendant(child, type_name)
        if found is not None:
            return found
    return None


def _parameters(fn_def: Node) -> list[tuple[str, str]]:
    decl = _function_declarator(fn_def)
    if decl is None:
        return []
    plist = _find_descendant(decl, "parameter_list")
    if plist is None:
        return []
    params: list[tuple[str, str]] = []
    for p in plist.named_children:
        if p.type == "parameter_declaration":
            ident = _find_identifier(p)
            name = _text(ident) if ident else ""
            if not name and _text(p).strip().lower() in ("void",):
                continue  # ``f(void)`` declares no parameters
            params.append((name, _text(p)))
    return params


def functions(tu: Node) -> list[CFunction]:
    """Return all function definitions in a translation unit.

    Recurses into preprocessor (``preproc_if``/``preproc_ifdef``) and ``ERROR``
    nodes, since tree-sitter nests ``function_definition`` nodes under them when
    the source uses ``#if``/``#ifdef`` conditionals.
    """
    out: list[CFunction] = []

    def walk(node: Node) -> None:
        if node.type == "function_definition":
            out.append(to_cfunction(node))
            return
        for child in node.named_children:
            walk(child)

    walk(tu)
    return out


def to_cfunction(fn_def: Node) -> CFunction:
    """Convert a ``function_definition`` node to a ``CFunction``."""
    name = _function_name(fn_def)
    body = None
    for child in fn_def.named_children:
        if child.type == "compound_statement":
            body = child
    # Return type is the leading type node(s) before the declarator; a pointer
    # return (``T *fn(...)``) carries its ``*`` in the declarator.
    decl = _function_declarator(fn_def)
    is_pointer = decl is not None and decl.type == "pointer_declarator"
    return_type = ""
    for child in fn_def.named_children:
        if child is decl or child.type == "compound_statement":
            break
        return_type += " " + _text(child)
    return_type = return_type.strip() or "void"
    if is_pointer:
        return_type += " *"
    return CFunction(name=name, return_type=return_type, parameters=_parameters(fn_def), body=body)


def find_function(tu: Node, name: str) -> Optional[CFunction]:
    for f in functions(tu):
        if f.name == name:
            return f
    return None
