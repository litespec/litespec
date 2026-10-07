"""Observation function (§9.8 ``ObservableProjection``, per port)."""

from __future__ import annotations


def observe(state_vars: list[tuple[str, str]], signals: list[str]) -> dict[str, str]:
    """Observation function: each ISIR signal observes a LIR state variable.

    Returns ``{signal: "sigma.<var>"}``.
    """
    return {sig: f"sigma.{var}" for (var, _), sig in zip(state_vars, signals)}
