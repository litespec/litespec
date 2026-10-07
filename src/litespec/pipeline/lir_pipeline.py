"""End-to-end LIR pipeline: Stage 1 → Stage 2 → Stage 5 → ``PathDagOp``."""

from __future__ import annotations

from typing import Callable, Optional

from litespec.derivation.for_c_desugaring import desugar_for_c_in
from litespec.derivation.progressive_lowering import progressive_lower
from litespec.lir.effect_expr_ast import EffectExpr
from litespec.pathdag import build_path_dag, derive_path_dag_op
from litespec.schema.document import SpecRecord
from litespec.schema.path_condition_dag import PathDagOp


def fallthrough_from_decomposition(record: SpecRecord) -> Callable[[EffectExpr, int], str]:
    """Derive the seq-segment fall-through predicate names from ``interface_checks``.

    The desugared ``ForCExpr``'s outer sequence boundaries map, in order, to the
    ``intermediate_assertion.name`` of the record's ``interface_checks``.
    """
    names: list[str] = []
    if record.decomposition is not None:
        for ic in record.decomposition.interface_checks:
            if ic.intermediate_assertion is not None:
                names.append(ic.intermediate_assertion.name)

    def fallthrough(_segment: EffectExpr, index: int) -> str:
        if 1 <= index <= len(names):
            return names[index - 1]
        return "true"

    return fallthrough


def run_lir_pipeline(
    effect: EffectExpr,
    dag_id: str,
    *,
    fallthrough: Optional[Callable[[EffectExpr, int], str]] = None,
) -> tuple[EffectExpr, PathDagOp]:
    """Run Stages 1, 2, and 5 on a single LIR effect, returning ``(desugared, op)``."""
    lowered = desugar_for_c_in(progressive_lower(effect))
    op = derive_path_dag_op(build_path_dag(lowered, dag_id, fallthrough=fallthrough))
    return lowered, op
