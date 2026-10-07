"""Global property layer records (§9.17, Phase 2+)."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import (
    DischargeStrategy,
    EmergentMethod,
    GlobalPropertyClass,
    ProtocolOrdering,
    ResourceKind,
    SchedulerPolicy,
)
from litespec.schema.primitives import Identifier, SpecId, WitnessArtifact


class GlobalProperty(LiteSpecModel):
    name: Identifier
    class_: GlobalPropertyClass = Field(alias="class")
    scope: list[SpecId] = []
    expr: str
    strategy: DischargeStrategy
    evidence: Optional[WitnessArtifact] = None


class GluingInvariant(LiteSpecModel):
    name: Identifier
    scope: list[SpecId] = []
    inv_expr: str
    inductive: bool
    sufficient: bool
    compatible: bool


class Resource(LiteSpecModel):
    name: Identifier
    kind: ResourceKind
    description: str


class SchedulerSpec(LiteSpecModel):
    name: Identifier
    policy: SchedulerPolicy
    preemptive: bool
    quantum: Optional[int] = None


class ProtocolSpec(LiteSpecModel):
    name: Identifier
    participants: list[SpecId] = []
    messages: list[str] = []
    ordering: ProtocolOrdering


class InterfaceSpec(LiteSpecModel):
    agreements: list[object] = []
    protocols: list[ProtocolSpec] = []
    type_agreements: list[object] = []


class CompositionSpec(LiteSpecModel):
    modules: list[SpecId] = []
    interface_spec: InterfaceSpec = InterfaceSpec()
    shared_resources: list[Resource] = []
    scheduler: SchedulerSpec


class EmergentDetection(LiteSpecModel):
    method: EmergentMethod
    candidates: list[Identifier] = []
    emergent: list[Identifier] = []
    notes: Optional[str] = None


class GlobalPropertyBlock(LiteSpecModel):
    """§9.17 ``GlobalPropertyBlock``."""

    properties: list[GlobalProperty] = []
    gluing_invariants: list[GluingInvariant] = []
    composition: CompositionSpec
    emergent_detection: EmergentDetection
