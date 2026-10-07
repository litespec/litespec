"""Layered EC verification — top-level (Phase 8)."""

from __future__ import annotations

from litespec.equivalence.composition import compose
from litespec.equivalence.dispatch import dispatch
from litespec.equivalence.obligation_generator import SEAM_ARTIFACTS, generate_obligations
from litespec.equivalence.refinement_chain_recorder import SEAM_LINKS, record_chain
from litespec.pipeline.pipeline_state import CheckResult
from litespec.schema.refinement_chain import RefinementChain


def run_layered_ec(**artifacts) -> tuple[CheckResult, RefinementChain]:
    """Discharge all five seam obligations and record the refinement chain.

    Each seam receives only its own artifact pair (``c_source``/``lir``, …);
    missing artifacts degrade that seam to ``warn`` rather than ``pass``.
    """
    seams = generate_obligations()
    results = []
    for seam in seams:
        left, right = SEAM_ARTIFACTS[seam]
        kwargs = {left: artifacts.get(left), right: artifacts.get(right)}
        if seam == "lir_to_unsafe":
            # The Rust-space differential needs the C source (to lower + extract).
            kwargs["c_source"] = artifacts.get("c_source")
        results.append(dispatch(seam, **kwargs))
    chain = record_chain([SEAM_LINKS[seam] for seam in seams])
    return compose(results), chain
