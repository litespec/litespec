"""Counterexample records (§9.8, schema ``counterexample``)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Counterexample:
    kind: str
    trace: tuple = ()
    description: str = ""
