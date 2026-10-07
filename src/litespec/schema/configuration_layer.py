"""Configuration layer schema (§10)."""

from __future__ import annotations

from typing import Any, Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import ConfigOperator, ConfigScope, ConfigSeverity, ConfigType
from litespec.schema.primitives import Identifier


class Range(LiteSpecModel):
    """§10.1 ``Range ::= { min, max, unit? }``."""

    min: int
    max: int
    unit: Optional[str] = None


class ConfigCondition(LiteSpecModel):
    """§10.1 ``ConfigCondition``."""

    parameter: Identifier
    operator: ConfigOperator
    value: Any


class RuntimeAPI(LiteSpecModel):
    """§10.1 ``RuntimeAPI ::= { getter, setter? }``."""

    getter: str
    setter: Optional[str] = None


class ConfigParameter(LiteSpecModel):
    """§10.1 ``ConfigParameter``."""

    name: Identifier
    display_name: str
    type: ConfigType
    default: Any
    range: Optional[Range] = None
    values: Optional[list[str]] = None
    pattern: Optional[str] = None
    description: str
    depends_on: Optional[list[ConfigCondition]] = None
    conflicts: Optional[list[ConfigCondition]] = None
    scope: ConfigScope
    module_ref: Optional[Identifier] = None
    runtime_api: Optional[RuntimeAPI] = None
    tags: Optional[list[str]] = None
    deprecated: Optional[bool] = None


class ConfigGroup(LiteSpecModel):
    """§10.1 ``ConfigGroup``."""

    name: Identifier
    display_name: str
    description: str
    parameters: list[Identifier] = []
    visible_when: Optional[list[ConfigCondition]] = None
    collapsed: Optional[bool] = None


class ConfigConstraint(LiteSpecModel):
    """§10.1 ``ConfigConstraint``."""

    name: Identifier
    description: str
    expression: str
    severity: ConfigSeverity


class ConfigPreset(LiteSpecModel):
    """§10.1 ``ConfigPreset``."""

    name: Identifier
    display_name: str
    description: str
    parameters: dict[Identifier, Any] = {}
    inherits: Optional[Identifier] = None


class ConfigDefaults(LiteSpecModel):
    """§10.1 ``ConfigDefaults``."""

    base: Optional[Identifier] = None
    overrides: Optional[dict[Identifier, Any]] = None
    profile: Optional[str] = None


class ConfigurationLayer(LiteSpecModel):
    """§10.1 ``ConfigurationLayer``."""

    parameters: list[ConfigParameter] = []
    groups: Optional[list[ConfigGroup]] = None
    defaults: Optional[ConfigDefaults] = None
    constraints: Optional[list[ConfigConstraint]] = None
    presets: Optional[list[ConfigPreset]] = None
