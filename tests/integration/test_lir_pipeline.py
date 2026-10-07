"""§18.1 runs end-to-end through Stage 5 → a valid PathDagOp."""

from litespec.lir.parser import parse_effect
from litespec.pathdag.indicator_naming import INDICATOR_NAMING_LITERAL
from litespec.pathdag.smt_lib2_serialization import smt2_form_hash
from litespec.pipeline.lir_pipeline import fallthrough_from_decomposition, run_lir_pipeline
from litespec.serialization import load_litespec

DAG_ID = "search_bounded_dag"


def test_mm_search_typed_binder_produces_path_dag_op(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    spec = doc.specs[0]
    action = spec.state_machine.actions[0]
    effect = parse_effect(action.effect)
    fallthrough = fallthrough_from_decomposition(spec)

    _, op = run_lir_pipeline(effect, DAG_ID, fallthrough=fallthrough)

    assert op.dag_id == DAG_ID
    assert op.root == "n_root"
    assert op.indicator_naming == INDICATOR_NAMING_LITERAL

    # Five nodes, matching §18.1: entry, seq(init), seq(loop), loop_body, loop_exit.
    assert len(op.nodes) == 5
    assert [str(n.kind) for n in op.nodes] == ["entry", "seq", "seq", "loop_body", "loop_exit"]
    assert [n.indicator for n in op.nodes] == [
        "p_search_bounded_dag_0",
        "p_search_bounded_dag_1",
        "p_search_bounded_dag_2",
        "p_search_bounded_dag_3",
        "p_search_bounded_dag_4",
    ]
    # Guards match the worked example.
    guards = [n.guard.expression for n in op.nodes]
    assert guards == ["true", "true", "R_init_done", "progress < limit", "not (progress < limit)"]
    # Parents: seq(init) under root; seq(loop) under seq(init); loop nodes under seq(loop).
    assert op.nodes[1].parent == op.nodes[0].node_id
    assert op.nodes[2].parent == op.nodes[1].node_id
    assert op.nodes[3].parent == op.nodes[2].node_id
    assert op.nodes[4].parent == op.nodes[2].node_id

    # Hashes are real, and the derived SMT-LIB2 hash is self-consistent.
    assert len(op.canonical_hash) == 64
    assert op.derived_smt2_hash == smt2_form_hash(op)


def test_desugared_form_matches_18_1(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    spec = doc.specs[0]
    effect = parse_effect(spec.state_machine.actions[0].effect)
    lowered, _ = run_lir_pipeline(effect, DAG_ID, fallthrough=fallthrough_from_decomposition(spec))

    from litespec.lir.effect_expr_ast import Sequence, While

    # SequenceExpr([init, WhileExpr(guard, SequenceExpr([body, step]))])
    assert isinstance(lowered, Sequence)
    assert len(lowered.items) == 2
    assert isinstance(lowered.items[1], While)
    assert isinstance(lowered.items[1].body, Sequence)
