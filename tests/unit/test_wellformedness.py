"""LIR well-formedness checks (WF1–WF92 subset)."""

from litespec.lir.wellformedness import check_wellformedness
from litespec.schema.global_property_block import (
    CompositionSpec,
    EmergentDetection,
    GlobalPropertyBlock,
    SchedulerSpec,
)
from litespec.serialization import load_litespec


def test_example_is_wellformed(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    report = check_wellformedness(doc)
    assert report.ok, report.error_lines()


def test_wf86_global_props_excluded(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    spec = doc.specs[0].model_copy(deep=True)
    spec.global_props = GlobalPropertyBlock(
        properties=[],
        gluing_invariants=[],
        composition=CompositionSpec(modules=[], scheduler=SchedulerSpec(name="s", policy="fifo", preemptive=False)),
        emergent_detection=EmergentDetection(method="manual", candidates=[], emergent=[]),
    )
    doc2 = doc.model_copy(update={"specs": [spec]})
    report = check_wellformedness(doc2)
    assert any(f.failure_mode == "phase_2_dependency_undisclosed" for f in report.failures)


def test_wf36_path_dag_implies_path_dag_op(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    spec = doc.specs[0].model_copy(deep=True)
    spec.decomposition.path_dag_op = None
    doc2 = doc.model_copy(update={"specs": [spec]})
    report = check_wellformedness(doc2)
    assert any(f.failure_mode == "path_dag_op_missing" for f in report.failures)


def test_wf85_path_dag_node_count_mismatch(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    spec = doc.specs[0].model_copy(deep=True)
    spec.decomposition.fragment_complexity.path_dag_node_count = 99
    doc2 = doc.model_copy(update={"specs": [spec]})
    report = check_wellformedness(doc2)
    assert any(f.failure_mode == "path_dag_op_missing" for f in report.failures)


def test_wf88_indicator_noncanonical(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    spec = doc.specs[0].model_copy(deep=True)
    spec.decomposition.path_dag_op.nodes[0].indicator = "p_wrong"
    doc2 = doc.model_copy(update={"specs": [spec]})
    report = check_wellformedness(doc2)
    assert any(f.failure_mode == "indicator_naming_noncanonical" for f in report.failures)


def test_wf84_hash_binding_out_of_bounds(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    spec = doc.specs[0].model_copy(deep=True)
    spec.decomposition.path_dag_op.canonical_hash = "$hash_bindings.30"
    doc2 = doc.model_copy(update={"specs": [spec]})
    report = check_wellformedness(doc2)
    assert any(f.failure_mode == "hash_binding_index_out_of_bounds" for f in report.failures)
