"""Normative pipeline order (§15.8)."""

from __future__ import annotations

#: The normative pass order, keyed by stage number (§15.8).
NORMATIVE_PIPELINE_ORDER: tuple[tuple[float, str, str], ...] = (
    (0.0, "LoopOptimizationPass", "optional"),
    (1.0, "ProgressiveLoweringPass", "Stage 1"),
    (1.5, "ForCLoweringPass", "Stage 2"),
    (2.0, "AbstractionRefinementCheckPass", ""),
    (3.0, "ISIRBackendCheckPass", ""),
    (4.0, "InjectionProjectionPass", 'stage -> "projected"'),
    (5.0, "PropertyDecompositionPass", 'stage -> "projected" (no-op)'),
    (6.0, "PromotionPass", "optional"),
    (7.0, "InjectedPropertyCheckPass", 'stage -> "checked"'),
    (8.0, "EquivalenceDecompositionPass", ""),
    (9.0, "CompositionalEquivalenceCheckPass", ""),
    (10.0, "GlobalCombinationPass", 'stage -> "composed" (Phase 2+)'),
)

#: ``ForCLoweringPass`` MUST precede these passes (Rule 15.8c).
FOR_C_PRECEDES: frozenset[str] = frozenset({"AbstractionRefinementCheckPass", "PropertyDecompositionPass"})


def pass_order() -> list[str]:
    """Return the ordered list of pass names."""
    return [name for _, name, _ in NORMATIVE_PIPELINE_ORDER]


def is_before(a: str, b: str) -> bool:
    """Whether pass ``a`` precedes pass ``b`` in the normative order."""
    names = pass_order()
    return names.index(a) < names.index(b)
