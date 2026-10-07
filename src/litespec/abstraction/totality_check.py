"""Abstraction totality check (Rule 9.15a / Rule R91)."""

from __future__ import annotations


def totality_check(state_vars: list[tuple[str, str]], signals: list[str]) -> tuple[bool, str]:
    """α is total iff every LIR state variable is covered by a signal."""
    vars_ = {name for name, _ in state_vars}
    # A signal ``sig_x`` covers state variable ``x``.
    covered = {sig[4:] for sig in signals if sig.startswith("sig_")}
    missing = vars_ - covered
    if missing:
        return False, f"α is not total: uncovered state variables {sorted(missing)}"
    return True, "α is total"
