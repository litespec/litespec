"""PropertyDecompositionPass (Stage 5, §15.11): path-DAG + PathDagOp derivation."""

from __future__ import annotations

from typing import Callable, Optional

from litespec.lir.effect_expr_ast import EffectExpr
from litespec.pathdag import build_path_dag, derive_path_dag_op
from litespec.schema.path_condition_dag import PathDagOp


def PropertyDecompositionPass(
    effect: EffectExpr,
    dag_id: str,
    *,
    fallthrough: Optional[Callable[[EffectExpr, int], str]] = None,
) -> PathDagOp:
    """Derive the ``PathDagOp`` for a desugared ``EffectExpr`` (D78 + D81)."""
    dag = build_path_dag(effect, dag_id, fallthrough=fallthrough)
    return derive_path_dag_op(dag)
