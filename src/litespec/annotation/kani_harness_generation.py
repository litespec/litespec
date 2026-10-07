"""Kani harness synthesis (Phase 5)."""

from __future__ import annotations

from litespec.schema.contract_layer import ContractLayer


def synthesize_kani_harness(name: str, contract: ContractLayer, unwind: int = 1) -> str:
    """Emit a ``#[kani::proof]`` harness with assume/assert from the contract."""
    lines = [
        "#[kani::proof]",
        f"#[kani::unwind({unwind})]",
        f"fn check_{name}() {{",
    ]
    for p in contract.preconditions:
        lines.append(f"    kani::assume({p.expression});")
    for p in contract.postconditions:
        lines.append(f"    kani::assert({p.expression});")
    lines.append("}")
    return "\n".join(lines)
