"""ISIR structural validation (interscope.md §5)."""

from __future__ import annotations

import re

from litespec.pipeline.pipeline_state import CheckResult

_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate_isir(isir: dict) -> CheckResult:
    """Structurally validate an ISIR module dict against the schema's required fields."""
    errors: list[str] = []

    if isir.get("isir_version") != "0.1":
        errors.append("isir_version must be '0.1'")

    module = isir.get("module")
    if module is None:
        errors.append("module missing")
        return CheckResult(status="fail", errors=errors)

    for field in ("name", "clocks", "resets", "state", "rules"):
        if field not in module:
            errors.append(f"module.{field} missing")

    name = module.get("name", "")
    if not _NAME_RE.match(name):
        errors.append(f"module.name {name!r} is not a valid identifier")

    for rule in module.get("rules", []):
        if "name" not in rule:
            errors.append("rule missing name")
        if "action" not in rule:
            errors.append(f"rule {rule.get('name', '?')} missing action")

    if errors:
        return CheckResult(status="fail", errors=errors)
    return CheckResult(status="pass", reports=[f"module {name!r} is structurally valid"])
