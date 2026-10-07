"""Pipeline state and the CheckResult monoid (§14.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from litespec.schema.document import SpecRecord


@dataclass
class CheckResult:
    """§14.3 CheckResult monoid (pass ⊑ warn ⊑ fail; ⊕ = union)."""

    status: str = "pass"  # "pass" | "warn" | "fail"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reports: list[str] = field(default_factory=list)

    def combine(self, other: CheckResult) -> CheckResult:
        severity = {"pass": 0, "warn": 1, "fail": 2}
        status = (
            "fail"
            if severity.get(self.status, 0) == 2 or severity.get(other.status, 0) == 2
            else ("warn" if severity.get(self.status, 0) == 1 or severity.get(other.status, 0) == 1 else "pass")
        )
        return CheckResult(
            status=status,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            reports=self.reports + other.reports,
        )

    @property
    def ok(self) -> bool:
        return self.status == "pass"


@dataclass
class PipelineState:
    """A minimal pipeline state carrying ``SpecRecord`` values and per-record LIR."""

    specs: list[SpecRecord]
    lir: dict[str, Any] = field(default_factory=dict)  # SpecId -> LIRSpec (EffectExpr actions)
    check: CheckResult = field(default_factory=CheckResult)
    stage: str = "raw"

    @classmethod
    def from_document(cls, doc: Any, lir_specs: Optional[dict[str, Any]] = None) -> PipelineState:
        return cls(specs=list(doc.specs), lir=lir_specs or {})
