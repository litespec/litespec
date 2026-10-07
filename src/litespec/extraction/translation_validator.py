"""Translation validator (Phase 2): basic LIR sanity checks on extracted functions."""

from __future__ import annotations

from litespec.extraction.c_to_lir import ExtractedFunction


def validate_translation(fn: ExtractedFunction) -> list[str]:
    """Return a list of validation errors (empty means valid)."""
    errors: list[str] = []
    declared = {name for name, _ in fn.state_vars} | {name for name, _ in fn.parameters}
    free = fn.effect.fv()
    # Field accesses (``cursor.size``) resolve to their base identifier (``cursor``).
    undeclared = {v for v in free if v.split(".")[0] not in declared}
    if undeclared:
        errors.append(f"undeclared free variables: {sorted(undeclared)}")
    if not fn.state_vars and not fn.parameters:
        errors.append("no state variables or parameters declared")
    return errors
