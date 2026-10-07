"""D44 ``DeriveAbstractionRelation`` (Phase 3)."""

from __future__ import annotations

from litespec.abstraction.map_expr_synthesis import synthesize_map_expr
from litespec.abstraction.rank_witness_derivation import derive_rank_witness
from litespec.schema.abstraction_block import AbstractionBlock, AbstractionRelation, ISIRTarget
from litespec.schema.loop_analysis import LoopAnalysis


def derive_abstraction_relation(
    state_vars: list[tuple[str, str]], signals: list[str], name: str = "alpha"
) -> AbstractionRelation:
    """D44: derive the abstraction relation from LIR state vars to ISIR signals."""
    return AbstractionRelation(
        name=name,
        source="LIR",
        target="ISIR",
        map_expr=synthesize_map_expr(state_vars, signals),
        totality=True,  # Rule 9.15a: relation.totality MUST be true
    )


def derive_abstraction_block(
    state_vars: list[tuple[str, str]],
    signals: list[str],
    loops: list[LoopAnalysis],
    isir_id: str,
    transition_ref: str,
    *,
    layers: list[str] | None = None,
    function_technique: str = "contract",
) -> AbstractionBlock:
    """Assemble a full ``AbstractionBlock`` (relation + layers + target + rank witness)."""
    return AbstractionBlock(
        relation=derive_abstraction_relation(state_vars, signals),
        layers=layers or ["A1", "A3", "A8"],
        refinement_target=ISIRTarget(isir_id=isir_id, transition_ref=transition_ref, signal_scope=signals),
        rank_witness=derive_rank_witness(loops),
        function_technique=function_technique,  # type: ignore[arg-type]
    )
