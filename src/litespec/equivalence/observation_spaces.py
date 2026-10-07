"""Observation spaces (§9.8)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObservationSpace:
    ports: tuple[str, ...]
    observables: tuple[str, ...]

    def __contains__(self, observable: str) -> bool:
        return observable in self.observables
