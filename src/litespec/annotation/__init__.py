"""Verification annotation synthesis — Verus + Kani (Phase 5)."""

from litespec.annotation.kani_harness_generation import synthesize_kani_harness
from litespec.annotation.kani_unwind_bound_derivation import derive_unwind_bound
from litespec.annotation.verus_annotation_synthesis import synthesize_verus_function
from litespec.annotation.verus_decreases_synthesis import synthesize_decreases
from litespec.annotation.verus_ensures_synthesis import synthesize_ensures
from litespec.annotation.verus_invariant_synthesis import synthesize_invariants
from litespec.annotation.verus_requires_synthesis import synthesize_requires

__all__ = [
    "derive_unwind_bound",
    "synthesize_decreases",
    "synthesize_ensures",
    "synthesize_invariants",
    "synthesize_kani_harness",
    "synthesize_requires",
    "synthesize_verus_function",
]
