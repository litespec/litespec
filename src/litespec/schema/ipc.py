"""IPC layer schema (§9.3)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import ChannelKind, ChannelOrdering, DoorbellMechanism, OverflowPolicy, SyncKind
from litespec.schema.primitives import Identifier, IntOrConfig


class IPCChannel(LiteSpecModel):
    """§9.3 ``IPCChannel``."""

    name: Identifier
    kind: ChannelKind
    capacity: IntOrConfig
    message_type: str  # TypeExpr
    ordering: ChannelOrdering
    overflow_policy: OverflowPolicy


class Doorbell(LiteSpecModel):
    """§9.3 ``Doorbell``."""

    name: Identifier
    mechanism: DoorbellMechanism
    target: Identifier
    semantics: str


class SyncPrimitive(LiteSpecModel):
    """§9.3 ``SyncPrimitive``."""

    name: Identifier
    kind: SyncKind
    semantics: str


class IPCLayer(LiteSpecModel):
    """§9.3 ``IPCLayer``."""

    channels: list[IPCChannel] = []
    doorbells: Optional[list[Doorbell]] = None
    synchronization: Optional[list[SyncPrimitive]] = None
