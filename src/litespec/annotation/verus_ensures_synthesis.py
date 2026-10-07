"""Verus ``ensures`` synthesis from contract postconditions (Phase 5)."""

from __future__ import annotations

from litespec.schema.contract_layer import ContractLayer


def synthesize_ensures(contract: ContractLayer) -> list[str]:
    """Emit Verus ``ensures`` clauses from ``contract.postconditions``."""
    return [f"ensures {p.expression}" for p in contract.postconditions]
