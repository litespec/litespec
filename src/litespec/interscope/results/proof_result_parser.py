"""InterScope result parsers (interscope.md §7)."""

from __future__ import annotations

from litespec.pipeline.pipeline_state import CheckResult


def parse_proof_result(stdout: str) -> CheckResult:
    """Parse InterScope proof output into a ``CheckResult``.

    Recognizes ``proved`` / ``disproved`` / ``counterexample`` markers.
    """
    text = stdout.lower()
    if "disproved" in text or "counterexample" in text:
        return CheckResult(status="fail", errors=[f"obligation disproved: {stdout.strip()[:200]}"])
    if "proved" in text:
        return CheckResult(status="pass", reports=[f"obligation proved: {stdout.strip()[:200]}"])
    return CheckResult(status="warn", warnings=["proof status unknown"])
