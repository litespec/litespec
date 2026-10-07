"""Layered equivalence-check verification (Phase 8)."""

from litespec.equivalence.coverage import classify_function, coverage_report, format_coverage
from litespec.equivalence.layered_ec import run_layered_ec
from litespec.equivalence.obligation_generator import SEAM_ARTIFACTS, generate_obligations
from litespec.equivalence.observation_function import observe
from litespec.equivalence.refinement_chain_recorder import SEAM_LINKS, record_chain
from litespec.equivalence.relations import RELATION_LATTICE, discharge, stronger_or_equal
from litespec.equivalence.verifier import verify_function

__all__ = [
    "RELATION_LATTICE",
    "SEAM_ARTIFACTS",
    "SEAM_LINKS",
    "classify_function",
    "coverage_report",
    "discharge",
    "format_coverage",
    "generate_obligations",
    "observe",
    "record_chain",
    "run_layered_ec",
    "stronger_or_equal",
    "verify_function",
]
