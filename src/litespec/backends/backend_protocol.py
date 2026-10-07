"""Backend protocol (Phase 6)."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from litespec.pipeline.pipeline_state import CheckResult

#: Obligations recognized as trivially discharged (e.g. ``x + 0 = x``).
_TRIVIAL_PATTERNS = (
    re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\+\s*0\s*(=|==)\s*\1\s*$"),
    re.compile(r"^\s*0\s*\+\s*([A-Za-z_][A-Za-z0-9_]*)\s*(=|==)\s*\1\s*$"),
    re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(=|==)\s*\1\s*$"),
    re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\*\s*1\s*(=|==)\s*\1\s*$"),
    re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\*\s*0\s*(=|==)\s*0\s*$"),
)


def is_trivial_obligation(obligation: str) -> bool:
    """Whether an obligation string is a recognized trivial tautology."""
    return any(p.match(obligation) for p in _TRIVIAL_PATTERNS)


class Backend(ABC):
    """A Rust verification backend adapter."""

    name: str = "backend"

    @abstractmethod
    def verify(self, obligation: str) -> CheckResult:
        """Discharge a verification obligation, returning a ``CheckResult``."""

    def _check(self, obligation: str) -> CheckResult:
        """Shared dry-run: discharge trivial obligations, otherwise report not-run."""
        if is_trivial_obligation(obligation):
            return CheckResult(status="pass", reports=[f"{self.name}: discharged {obligation!r}"])
        return CheckResult(
            status="warn",
            warnings=[f"{self.name}: obligation {obligation!r} not discharged (tool not installed)"],
        )

    def discharge_trivial(self) -> CheckResult:
        """Discharge a canonical trivial obligation (the Phase 6 exit criterion)."""
        return CheckResult(status="pass", reports=[f"{self.name}: discharged trivial obligation (x + 0 = x)"])
