"""Abstraction observable-preservation check (Rule R91)."""

from __future__ import annotations


def observable_preservation_check(state_vars: list[tuple[str, str]], signals: list[str]) -> tuple[bool, str]:
    """Observable preservation: every ISIR signal is an observation of a state var."""
    vars_ = {name for name, _ in state_vars}
    for sig in signals:
        if not sig.startswith("sig_") or sig[4:] not in vars_:
            return False, f"signal {sig!r} is not an observation of a declared state variable"
    return True, "observables are preserved"
