"""ISIR completeness check (Phase 9)."""

from __future__ import annotations

from pathlib import Path

from litespec.pipeline.pipeline_state import CheckResult


def check_isir_completeness(modules: dict[str, list[str]], isir_base: Path) -> CheckResult:
    """Every in-scope function must have an emitted ``.isir`` file.

    ``modules`` maps a module name to its in-scope functions; ``isir_base`` is
    the ``output/isir`` root. Files are expected at ``isir_base/<module>/<fn>.isir``.
    """
    missing: list[str] = []
    total = 0
    for module, functions in modules.items():
        for fn in functions:
            total += 1
            if not (isir_base / module / f"{fn}.isir").exists():
                missing.append(f"{module}/{fn}")
    if missing:
        return CheckResult(status="fail", errors=[f"missing .isir for: {sorted(missing)}"])
    return CheckResult(status="pass", reports=[f"{total} .isir files present"])
