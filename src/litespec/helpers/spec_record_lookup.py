"""Canonical helpers: ``SpecRecord_lookup`` and ``record_phase_of`` (D86)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.document import SpecRecord


def spec_record_lookup(specs: list[SpecRecord]) -> dict[str, SpecRecord]:
    """§13.1 ``SpecRecord_lookup(specs) : Map<SpecId, SpecRecord>``."""
    return {s.id: s for s in specs}


def record_phase_of(spec: SpecRecord, module_phase: Optional[str] = None) -> str:
    """D86 ``record_phase_of``: resolve a record's phase.

    If ``record_phase`` is set, use it; otherwise inherit from the enclosing
    module's ``phase``: ``lightweight → phase_1``, ``extended → phase_2``,
    otherwise ``phase_3``.
    """
    if spec.record_phase is not None:
        return str(spec.record_phase)
    if module_phase == "lightweight":
        return "phase_1"
    if module_phase == "extended":
        return "phase_2"
    return "phase_3"
