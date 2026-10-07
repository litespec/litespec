"""Fragment complexity record (§3)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel


class FragmentComplexity(LiteSpecModel):
    """§3 ``FragmentComplexity``."""

    max_depth: int
    max_branch_cardinality: int
    max_disjunct_count: int
    path_dag_node_count: int
    total_fragment_nodes: int
    measurement_notes: Optional[str] = None
