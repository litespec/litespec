"""LIR→ISIR abstraction (α relation, RankWitness, layers A1–A8)."""

from litespec.abstraction.abstraction_layer_derivation import abstraction_layer, abstraction_layers
from litespec.abstraction.map_expr_synthesis import synthesize_map_expr, synthesize_signal_scope
from litespec.abstraction.observable_preservation_check import observable_preservation_check
from litespec.abstraction.rank_witness_derivation import derive_rank_witness, requires_rank
from litespec.abstraction.refinement_relation import defines_refinement, refinement_chain
from litespec.abstraction.relation_derivation import derive_abstraction_block, derive_abstraction_relation
from litespec.abstraction.stutter_encoding_derivation import derive_stutter_encoding
from litespec.abstraction.totality_check import totality_check
from litespec.abstraction.type_coherence_check import type_coherence_check

__all__ = [
    "abstraction_layer",
    "abstraction_layers",
    "defines_refinement",
    "derive_abstraction_block",
    "derive_abstraction_relation",
    "derive_rank_witness",
    "derive_stutter_encoding",
    "observable_preservation_check",
    "refinement_chain",
    "requires_rank",
    "synthesize_map_expr",
    "synthesize_signal_scope",
    "totality_check",
    "type_coherence_check",
]
