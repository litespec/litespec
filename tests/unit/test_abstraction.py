"""LIR→ISIR abstraction (α relation, RankWitness, layers A1–A8)."""

from litespec.abstraction import (
    abstraction_layers,
    derive_abstraction_block,
    derive_abstraction_relation,
    derive_rank_witness,
    observable_preservation_check,
    requires_rank,
    synthesize_map_expr,
    synthesize_signal_scope,
    totality_check,
    type_coherence_check,
)
from litespec.schema.loop_analysis import BoundedIteration, LoopAnalysis, LoopVariant
from litespec.schema.primitives import LIRNodeRef

_STATE_VARS = [("pool", "Nat"), ("cursor", "Block"), ("errno", "Nat")]
_SIGNALS = ["sig_pool", "sig_cursor", "sig_errno"]


def _loop() -> LoopAnalysis:
    return LoopAnalysis(
        loop_id="alloc_search",
        function="LOS_MemAlloc",
        lir_fragment=LIRNodeRef(function="LOS_MemAlloc", node_id="L_search"),
        loop_kind="while",
        iteration_var="cursor",
        bound=BoundedIteration(
            target="cursor", kind="loop", bound=256, bound_source="config_param", on_exceed="assert"
        ),
        variant=LoopVariant(
            expr="lambda sigma. remaining_free_list_length(sigma)",
            domain="Nat",
            decreases_on="iteration",
            well_founded="proved",
        ),
    )


def test_synthesize_map_expr():
    expr = synthesize_map_expr(_STATE_VARS, _SIGNALS)
    assert expr == "lambda sigma. { sig_pool := sigma.pool, sig_cursor := sigma.cursor, sig_errno := sigma.errno }"


def test_synthesize_signal_scope():
    assert synthesize_signal_scope(_STATE_VARS) == ["sig_pool", "sig_cursor", "sig_errno"]


def test_derive_abstraction_relation():
    rel = derive_abstraction_relation(_STATE_VARS, _SIGNALS, name="alpha_mm")
    assert rel.name == "alpha_mm"
    assert rel.source == "LIR" and rel.target == "ISIR"
    assert rel.totality is True
    assert "sig_pool := sigma.pool" in rel.map_expr


def test_abstraction_layers():
    layers = abstraction_layers()
    assert [str(l.id) for l in layers] == ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"]
    assert all(l.derived for l in layers)


def test_derive_rank_witness():
    loop = _loop()
    assert requires_rank([loop]) is True
    rw = derive_rank_witness([loop])
    assert rw is not None
    assert rw.function == "lambda sigma. remaining_free_list_length(sigma)"
    assert rw.decreases_on == "iteration"


def test_derive_abstraction_block():
    block = derive_abstraction_block(_STATE_VARS, _SIGNALS, [_loop()], "mm_alloc_isir", "tc_alloc")
    assert block.relation.name == "alpha"
    assert list(block.layers) == ["A1", "A3", "A8"]
    assert block.refinement_target.isir_id == "mm_alloc_isir"
    assert block.refinement_target.transition_ref == "tc_alloc"
    assert block.rank_witness is not None
    assert str(block.function_technique) == "contract"


def test_abstraction_checks():
    assert totality_check(_STATE_VARS, _SIGNALS)[0] is True
    assert type_coherence_check(_STATE_VARS, _SIGNALS)[0] is True
    assert observable_preservation_check(_STATE_VARS, _SIGNALS)[0] is True


def test_totality_check_detects_missing():
    assert totality_check(_STATE_VARS, ["sig_pool"])[0] is False
