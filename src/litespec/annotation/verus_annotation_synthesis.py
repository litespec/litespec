"""Verus annotation synthesis — top-level assembly (Phase 5)."""

from __future__ import annotations

from litespec.annotation.verus_decreases_synthesis import synthesize_decreases
from litespec.annotation.verus_ensures_synthesis import synthesize_ensures
from litespec.annotation.verus_invariant_synthesis import synthesize_invariants
from litespec.annotation.verus_requires_synthesis import synthesize_requires
from litespec.lir.effect_expr_ast import EffectExpr
from litespec.lowering.effect_expr_to_rust import render_effect_rust
from litespec.lowering.rust_type_mapping import rust_type
from litespec.schema.contract_layer import ContractLayer
from litespec.schema.loop_analysis import LoopAnalysis


def synthesize_verus_function(
    name: str,
    params: list[tuple[str, str]],
    return_type: str,
    state_vars: list[tuple[str, str]],
    effect: EffectExpr,
    contract: ContractLayer,
    loops: list[LoopAnalysis],
) -> str:
    """Emit a Verus-annotated function (requires/ensures + loop invariants/decreases)."""
    requires = synthesize_requires(contract)
    ensures = synthesize_ensures(contract)
    invariants = synthesize_invariants(contract)
    decreases = synthesize_decreases(loops)

    param_str = ", ".join(f"{n}: {rust_type(t)}" for n, t in params)
    rt = rust_type(return_type)
    body = render_effect_rust(effect, {n: t for n, t in state_vars})

    lines = ["verus! {", f"    pub fn {name}({param_str}) -> {rt}"]
    for clause in requires:
        lines.append(f"        {clause}")
    for clause in ensures:
        lines.append(f"        {clause}")
    lines.append("    {")
    for inv in invariants:
        lines.append(f"        // {inv}")
    for dec in decreases:
        lines.append(f"        // {dec}")
    for bline in body.splitlines():
        lines.append(f"        {bline}" if bline else "")
    lines.append("    }")
    lines.append("}")
    return "\n".join(lines)
