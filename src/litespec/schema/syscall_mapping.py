"""Syscall mapping layer schema (§9.5)."""

from __future__ import annotations

from litespec.schema.base import LiteSpecModel
from litespec.schema.primitives import Identifier


class SyscallMapping(LiteSpecModel):
    """§9.5 ``SyscallMapping``."""

    syscall: str
    handler: Identifier
    arguments: list[str] = []
    return_semantics: str
    error_codes: list[str] = []
