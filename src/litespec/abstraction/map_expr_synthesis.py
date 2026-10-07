"""Map-expression synthesis for the abstraction relation α (Phase 3)."""

from __future__ import annotations


def synthesize_map_expr(state_vars: list[tuple[str, str]], signals: list[str]) -> str:
    """Synthesize the α map expression ``lambda sigma. { sig_i := sigma.var_i }``.

    ``state_vars`` is a list of ``(name, TypeExpr)``; ``signals`` is the ISIR
    signal scope. Signals are zipped against state variables in order.
    """
    mappings = []
    for (var, _type), sig in zip(state_vars, signals):
        mappings.append(f"{sig} := sigma.{var}")
    if not mappings:
        return "lambda sigma. { }"
    return "lambda sigma. { " + ", ".join(mappings) + " }"


def synthesize_signal_scope(state_vars: list[tuple[str, str]]) -> list[str]:
    """Derive an ISIR signal name for each LIR state variable (``sig_<var>``)."""
    return [f"sig_{var}" for var, _ in state_vars]
