"""EC seam dispatch (Phase 8)."""

from __future__ import annotations

from litespec.equivalence import (
    seam_c_to_lir_equivalence,
    seam_lir_to_isir_equivalence,
    seam_lir_to_unsafe_equivalence,
    seam_safe_to_isir_equivalence,
    seam_unsafe_to_safe_equivalence,
)
from litespec.pipeline.pipeline_state import CheckResult

_SEAMS = {
    seam_c_to_lir_equivalence.SEAM: seam_c_to_lir_equivalence,
    seam_lir_to_unsafe_equivalence.SEAM: seam_lir_to_unsafe_equivalence,
    seam_unsafe_to_safe_equivalence.SEAM: seam_unsafe_to_safe_equivalence,
    seam_lir_to_isir_equivalence.SEAM: seam_lir_to_isir_equivalence,
    seam_safe_to_isir_equivalence.SEAM: seam_safe_to_isir_equivalence,
}


def dispatch(seam: str, **kwargs) -> CheckResult:
    """Route a seam obligation to its check function."""
    try:
        module = _SEAMS[seam]
    except KeyError:
        raise KeyError(f"unknown seam {seam!r}") from None
    return module.check(**kwargs)
