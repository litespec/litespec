"""Service interface layer schema (§9.4) and service dependencies (§3)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import IsolationLevel, RestartPolicy, SupervisorImpl
from litespec.schema.primitives import Identifier, IntOrConfig, SemVer


class ServiceDependency(LiteSpecModel):
    """§3 ``ServiceDependency ::= { service_ref, required, fallback? }``."""

    service_ref: Identifier
    required: bool
    fallback: Optional[str] = None


class ServiceOperation(LiteSpecModel):
    """§9.4 ``ServiceOperation``."""

    name: Identifier
    request_type: str  # TypeExpr
    response_type: str  # TypeExpr
    timeout: Optional[IntOrConfig] = None
    idempotent: bool


class ServiceInterface(LiteSpecModel):
    """§9.4 ``ServiceInterface``."""

    name: Identifier
    version: SemVer
    operations: list[ServiceOperation] = []
    supervisor_impl: SupervisorImpl
    restart_policy: RestartPolicy
    isolation_level: IsolationLevel
    dependencies: Optional[list[ServiceDependency]] = None
