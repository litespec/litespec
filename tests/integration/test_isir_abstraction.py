"""LOS_MemAlloc LIR state maps to a valid ISIR transition system."""

from litespec.abstraction import (
    derive_abstraction_block,
    observable_preservation_check,
    synthesize_signal_scope,
    totality_check,
    type_coherence_check,
)
from litespec.extraction import extract_function

_C = """\
void *LOS_MemAlloc(void *pool, unsigned int size) {
    void *result = 0;
    Block *cursor = (Block *)pool;
    while (cursor->size < size) { cursor = cursor->next; }
    if (cursor->size >= size) { result = cursor; }
    return result;
}
"""


def test_los_memalloc_state_maps_to_isir():
    fn = extract_function(_C, "LOS_MemAlloc")
    signals = synthesize_signal_scope(fn.state_vars)

    block = derive_abstraction_block(fn.state_vars, signals, [], "mm_alloc_isir", "tc_alloc")

    # A valid α : Σ_LIR → Σ_ISIR is total, type-coherent, observable-preserving.
    assert block.relation.totality is True
    assert totality_check(fn.state_vars, signals)[0] is True
    assert type_coherence_check(fn.state_vars, signals)[0] is True
    assert observable_preservation_check(fn.state_vars, signals)[0] is True
    assert block.refinement_target.isir_id == "mm_alloc_isir"
