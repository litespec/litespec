"""EC composition: combine seam results (§14.3 CheckResult monoid)."""

from __future__ import annotations

from litespec.pipeline.pipeline_state import CheckResult


def compose(results: list[CheckResult]) -> CheckResult:
    """Combine per-seam ``CheckResult`` values into a single result."""
    acc = CheckResult()
    for result in results:
        acc = acc.combine(result)
    return acc
