"""``PathDagOp`` derivation (D81 ``DerivePathDagOp``)."""

from __future__ import annotations

import hashlib
from typing import Any

from litespec.pathdag.indicator_naming import INDICATOR_NAMING_LITERAL, indicator_for
from litespec.pathdag.smt_lib2_serialization import smt2_form_hash
from litespec.pathdag.stable_topological_sort import stable_topological_sort
from litespec.schema.path_condition_dag import PathDagOp
from litespec.serialization.canonical_yaml import canonical_yaml


def canonical_hash_of_nodes(nodes: list[Any]) -> str:
    """SHA-256 over the canonical YAML of the node list (D81)."""
    data = [n.model_dump(mode="json", exclude_none=True) for n in nodes]
    return hashlib.sha256(canonical_yaml(data).encode("utf-8")).hexdigest()


def derive_path_dag_op(dag: Any) -> PathDagOp:
    """Derive a ``PathDagOp`` from a ``PathConditionDAG`` (D81)."""
    ordered = stable_topological_sort(dag.nodes)
    canonical_nodes = [n.model_copy(update={"indicator": indicator_for(dag.dag_id, i)}) for i, n in enumerate(ordered)]
    return PathDagOp(
        dag_id=dag.dag_id,
        root=dag.root,
        nodes=canonical_nodes,
        indicator_naming=INDICATOR_NAMING_LITERAL,
        canonical_hash=canonical_hash_of_nodes(canonical_nodes),
        derived_smt2_hash=smt2_form_hash(dag),
    )
