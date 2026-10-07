"""Verus ``requires`` synthesis from contract preconditions (Phase 5)."""

from __future__ import annotations

from litespec.schema.contract_layer import ContractLayer


def synthesize_requires(contract: ContractLayer) -> list[str]:
    """Emit Verus ``requires`` clauses from ``contract.preconditions``."""
    return [f"requires {p.expression}" for p in contract.preconditions]
