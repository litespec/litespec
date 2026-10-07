"""Derivation rules (§13). Phase 1/2 subset."""

from litespec.derivation.for_c_desugaring import derive_for_c_desugaring, desugar_for_c_in
from litespec.derivation.progressive_lowering import derive_loop_construct_desugaring, progressive_lower
from litespec.derivation.type_declarations_derivation import collect_identifier_type_exprs, derive_type_declarations

__all__ = [
    "collect_identifier_type_exprs",
    "derive_for_c_desugaring",
    "derive_loop_construct_desugaring",
    "derive_type_declarations",
    "desugar_for_c_in",
    "progressive_lower",
]
