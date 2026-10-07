"""Abstraction-layer catalogue A1–A8 (§9.15, Appendix O)."""

from __future__ import annotations

from litespec.schema.abstraction_block import AbstractionLayer

#: The eight abstraction layers. Names are reconstructed from the framework's
#: stated properties (totality, type-coherence, observable-preservation,
#: transition correspondence, stutter encoding, rank witness) because the
#: authoritative catalogue (v0.26.0 Volume 2 Appendix O) is not in this volume.
_LAYERS: tuple[tuple[str, str, str], ...] = (
    ("A1", "State-space correspondence", "Σ_LIR → Σ_ISIR mapping is a total function"),
    ("A2", "Type coherence", "TypeExpr maps coherently under α"),
    ("A3", "Observable preservation", "Observables are preserved under α"),
    ("A4", "Transition correspondence", "Each LIR step maps to ≥1 ISIR step"),
    ("A5", "Stutter encoding", "Stuttering steps are encoded via a tagged union"),
    ("A6", "Rank witness", "A decreasing measure discharges termination"),
    ("A7", "Refinement composition", "α composes with lower-level refinements"),
    ("A8", "Totality", "α is total on Σ_LIR (Rule 9.15a)"),
)


def abstraction_layers() -> list[AbstractionLayer]:
    """Return the A1–A8 abstraction layers (all derived)."""
    return [
        AbstractionLayer(
            id=layer_id,
            name=name,
            derived=True,
            derivation=derivation,
            soundness="Discharged by the abstraction checks (Rule 9.15a).",
        )
        for layer_id, name, derivation in _LAYERS
    ]


def abstraction_layer(layer_id: str) -> AbstractionLayer:
    for layer in abstraction_layers():
        if layer.id == layer_id:
            return layer
    raise KeyError(layer_id)
