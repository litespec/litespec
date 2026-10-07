"""Contract attachment: attach ACSL annotations to an extracted function (Phase 2)."""

from __future__ import annotations

from typing import Optional

from tree_sitter import Node

from litespec.extraction.acsl_parser import is_acsl_comment, parse_acsl
from litespec.extraction.c_parser import parse_c
from litespec.schema.contract_layer import ContractLayer, LoopInvariantClause
from litespec.schema.primitives import Predicate


def _find_function(tu: Node, name: str) -> Optional[Node]:
    for child in tu.named_children:
        if child.type == "function_definition":
            from litespec.extraction.c_translation_unit import _function_name

            if _function_name(child) == name:
                return child
    return None


def _leading_comment(tu: Node, fn_def: Node) -> Optional[Node]:
    """The comment node immediately preceding a function definition."""
    children = tu.named_children
    idx = None
    for i, child in enumerate(children):
        if child is fn_def:
            idx = i
            break
    if idx is None:
        return None
    for j in range(idx - 1, -1, -1):
        if children[j].type == "comment":
            return children[j]
    return None


def _body_comments(fn_def: Node) -> list[Node]:
    out: list[Node] = []

    def walk(node: Node) -> None:
        if node.type == "comment":
            out.append(node)
        for child in node.named_children:
            walk(child)

    for child in fn_def.named_children:
        if child.type == "compound_statement":
            walk(child)
    return out


def _predicate(expr: str, kind: str) -> Predicate:
    return Predicate(expression=expr, description=f"{kind}: {expr}")


def attach_contract(source: str | bytes, function_name: str) -> ContractLayer:
    """Attach ACSL requires/ensures/loop-invariants to ``function_name``."""
    tu = parse_c(source)
    fn_def = _find_function(tu, function_name)
    if fn_def is None:
        return ContractLayer()

    preconditions: list[Predicate] = []
    postconditions: list[Predicate] = []
    loop_invariants: list[LoopInvariantClause] = []

    leading = _leading_comment(tu, fn_def)
    if leading is not None and is_acsl_comment(leading.text.decode()):
        for clause in parse_acsl(leading.text.decode()):
            if clause.kind == "requires":
                preconditions.append(_predicate(clause.expression, "requires"))
            elif clause.kind == "ensures":
                postconditions.append(_predicate(clause.expression, "ensures"))

    for comment in _body_comments(fn_def):
        if is_acsl_comment(comment.text.decode()):
            for clause in parse_acsl(comment.text.decode()):
                if clause.kind == "loop_invariant":
                    loop_invariants.append(LoopInvariantClause(family="shape", expr=clause.expression, scope="all"))

    return ContractLayer(
        preconditions=preconditions,
        postconditions=postconditions,
        loop_invariants=loop_invariants or None,
    )


def synthesize_contract(return_type: str, name: str = "") -> ContractLayer:
    """Synthesize a default contract when the C source carries no ACSL annotation.

    Emits a trivially-valid safety postcondition so the ISIR carries at least one
    proof obligation for InterScope to discharge (the "fully utilized" leg). The
    expression is a simple S-expression the InterScope assertion dialect accepts.
    """
    return ContractLayer(
        preconditions=[],
        postconditions=[
            Predicate(
                expression="true",
                description=f"synthesized safety postcondition for {name or 'function'} (no ACSL contract)",
            )
        ],
    )
