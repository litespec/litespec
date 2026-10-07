"""ProgressiveLoweringPass (Stage 1, §15.10): lower non-``ForC`` loops."""

from __future__ import annotations

from litespec.derivation.progressive_lowering import progressive_lower
from litespec.lir.effect_expr_ast import EffectExpr
from litespec.pipeline.pipeline_state import PipelineState


def ProgressiveLoweringPass(state: PipelineState) -> PipelineState:
    """Rewrite each LIR action's effect via D77, retaining ``ForCExpr``."""
    state.lir = {sid: progressive_lower(effect) for sid, effect in state.lir.items()}
    state.stage = "Stage 1"
    return state


def lower_effect(effect: EffectExpr) -> EffectExpr:
    """Stage-1 lowering of a single effect (D77)."""
    return progressive_lower(effect)
