"""Verus backend adapter (Phase 6)."""

from __future__ import annotations

from litespec.backends.backend_protocol import Backend
from litespec.pipeline.pipeline_state import CheckResult


class VerusBackend(Backend):
    name = "verus"

    def verify(self, obligation: str) -> CheckResult:
        return self._check(obligation)
