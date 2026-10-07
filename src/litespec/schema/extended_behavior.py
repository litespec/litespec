"""Extended-behavior layer records (§9.9, §9.10)."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import (
    CheckProvenance,
    DischargeStrategy,
    ExtendedBehaviorClass,
    InjectionPolicy,
    TemplateTier,
)
from litespec.schema.primitives import Identifier


class ExtendedBehaviorCheck(LiteSpecModel):
    """§9.9 ``ExtendedBehaviorCheck``."""

    id: str
    class_: ExtendedBehaviorClass = Field(alias="class")
    target: Identifier
    expression: str
    verification: DischargeStrategy
    capability_ref: Optional[str] = None
    provenance: CheckProvenance
    template_id: Optional[str] = None
    instance_id: Optional[str] = None
    rationale: Optional[str] = None
    sub_part_ref: Optional[Identifier] = None
    tier: TemplateTier


class ExtendedBehaviorModel(LiteSpecModel):
    """§9.9 ``ExtendedBehaviorModel``."""

    injection_policy: InjectionPolicy
    injection_overrides: Optional[dict[str, bool]] = None
    checks: list[ExtendedBehaviorCheck] = []
    strategy: DischargeStrategy
    notes: Optional[str] = None


class InjectionReportProjection(LiteSpecModel):
    """§3 ``InjectionReportProjection``."""

    sub_part_assignments: dict[Identifier, list[str]] = {}
    parent_level_checks: list[str] = []
    unassigned_checks: list[str] = []
