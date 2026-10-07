"""Verus loop-``invariant`` synthesis from contract loop invariants (Phase 5)."""

from __future__ import annotations

from litespec.schema.contract_layer import ContractLayer


def synthesize_invariants(contract: ContractLayer) -> list[str]:
    """Emit Verus ``invariant`` clauses from ``contract.loop_invariants``."""
    if not contract.loop_invariants:
        return []
    return [f"invariant {li.expr}" for li in contract.loop_invariants]
