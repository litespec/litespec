"""EC obligation generation (§9.8): the five seam obligations."""

from __future__ import annotations

#: The refinement chain T_C ⊑ T_LIR ⊑ T_Unsafe ⊑ T_Safe ⊑_α T_ISIR.
SEAM_ORDER = ("c_to_lir", "lir_to_unsafe", "unsafe_to_safe", "lir_to_isir", "safe_to_isir")

#: Which artifact names each seam consumes.
SEAM_ARTIFACTS: dict[str, tuple[str, str]] = {
    "c_to_lir": ("c_source", "lir"),
    "lir_to_unsafe": ("lir", "rust"),
    "unsafe_to_safe": ("unsafe", "safe"),
    "lir_to_isir": ("lir", "isir"),
    "safe_to_isir": ("safe", "isir"),
}


def generate_obligations() -> list[str]:
    """Return the five seam obligation names in chain order."""
    return list(SEAM_ORDER)
