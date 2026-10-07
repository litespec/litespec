"""Placeholder-discipline check (Rule 0.6tt, Phase 9)."""

from __future__ import annotations

import json

from litespec.pipeline.pipeline_state import CheckResult
from litespec.schema.document import LiteSpecDocument

_MARKERS = ("TODO", "FIXME", "PLACEHOLDER")


def check_placeholders(doc: LiteSpecDocument) -> CheckResult:
    """Normative text must not contain placeholder markers."""
    text = json.dumps(doc.model_dump(mode="json", exclude_none=True), indent=2).upper()
    found = [m for m in _MARKERS if m in text]
    if found:
        return CheckResult(status="fail", errors=[f"placeholder marker(s): {found}"])
    return CheckResult(status="pass", reports=["no placeholder markers"])
