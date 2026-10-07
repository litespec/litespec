"""SMT-LIB2 serialization of a path DAG (D80 ``SerializePathDAG``)."""

from __future__ import annotations

import hashlib
from typing import Any

from litespec.pathdag.indicator_naming import indicator_for
from litespec.pathdag.stable_topological_sort import stable_topological_sort


def _ordered_indicators(dag: Any) -> list[tuple[Any, str]]:
    ordered = stable_topological_sort(dag.nodes)
    return [(n, indicator_for(dag.dag_id, i)) for i, n in enumerate(ordered)]


def derive_smt2_form(dag: Any) -> str:
    """Derive the SMT-LIB2 body for ``dag`` (§9.22.2)."""
    pairs = _ordered_indicators(dag)
    indicator_of = {n.node_id: ind for n, ind in pairs}
    lines: list[str] = []

    for n, ind in pairs:
        lines.append(f"(declare-fun {ind} () Bool)")

    for n, ind in pairs:
        if n.parent is not None:
            lines.append(f"(assert (=> {ind} {indicator_of[n.parent]}))")

    for n, ind in pairs:
        if n.guard.expression != "true":
            lines.append(f"(assert (=> {ind} {n.guard.expression}))")

    lines.append(f"(assert {indicator_of[dag.root]})")
    return "\n".join(lines) + "\n"


def smt2_form_hash(dag: Any) -> str:
    """SHA-256 over the derived SMT-LIB2 form (D80 ``SerializePathDAGForHash``)."""
    return hashlib.sha256(derive_smt2_form(dag).encode("utf-8")).hexdigest()
