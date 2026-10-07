"""Canonical path-DAG indicator naming (§9.22.1, D81)."""

from __future__ import annotations

# The fixed schema literal recorded in ``PathDagOp.indicator_naming`` (§9.22.1).
INDICATOR_NAMING_LITERAL = "p_<dag_id>_<i>_by_stable_topological_order"


def indicator_for(dag_id: str, index: int) -> str:
    """The actual indicator string for the node at ``index`` (D81 ``indicator_of``)."""
    return f"p_{dag_id}_{index}"
