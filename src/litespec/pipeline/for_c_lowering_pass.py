"""ForCLoweringPass (Stage 2, §15.10.1): desugar every ``ForCExpr`` (D84)."""

from __future__ import annotations

from litespec.derivation.for_c_desugaring import desugar_for_c_in
from litespec.lir.effect_expr_ast import EffectExpr
from litespec.pipeline.pipeline_state import PipelineState


def ForCLoweringPass(state: PipelineState) -> PipelineState:
    """Rewrite each LIR action's effect via D84; a second pass is a no-op."""
    state.lir = {sid: desugar_for_c_in(effect) for sid, effect in state.lir.items()}
    state.stage = "Stage 2"
    return state


def lower_effect(effect: EffectExpr) -> EffectExpr:
    """Stage-2 lowering of a single effect (D84)."""
    return desugar_for_c_in(effect)
