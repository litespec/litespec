"""Property template library records (§9.10)."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import (
    DischargeStrategy,
    ExtendedBehaviorClass,
    InstantiationCardinality,
    TemplateTier,
    TemplateTrigger,
)
from litespec.schema.primitives import SemVer


class InstantiationRule(LiteSpecModel):
    """§9.10 ``InstantiationRule``."""

    cardinality: InstantiationCardinality
    element_kind: Optional[str] = None
    id_pattern: str


class PropertyTemplate(LiteSpecModel):
    """§9.10 ``PropertyTemplate``."""

    id: str
    tier: TemplateTier
    version: SemVer
    trigger: TemplateTrigger
    class_: ExtendedBehaviorClass = Field(alias="class")
    expression: str
    default_verif: DischargeStrategy
    capability_ref: Optional[str] = None
    rationale: str
    instantiation: InstantiationRule
    tags: Optional[list[str]] = None
