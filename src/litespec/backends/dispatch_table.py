"""Backend dispatch table (Phase 6)."""

from __future__ import annotations

from litespec.backends.backend_registry import get_backend
from litespec.pipeline.pipeline_state import CheckResult


def dispatch(obligation: str, tool: str) -> CheckResult:
    """Route an obligation to the named backend and return its ``CheckResult``."""
    return get_backend(tool).verify(obligation)
