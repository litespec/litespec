"""loading and dumping the §18.1 worked example."""

from litespec.schema.document import LiteSpecDocument
from litespec.serialization import dumps_litespec, load_litespec, loads_litespec


def test_load_worked_example(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    assert isinstance(doc, LiteSpecDocument)
    assert doc.litespec_version == "0.28.3"
    assert doc.module.name == "kernel_mm"
    assert len(doc.specs) == 1


def test_spec_fields(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    spec = doc.specs[0]
    assert spec.id == "mm_search_typed_binder"
    assert spec.record_phase == "phase_1"
    assert spec.source.function == "LOS_MemSearchBounded"
    assert spec.contract.preconditions[0].expression == "pool != null"
    assert len(spec.state_machine.state_variables) == 4
    assert spec.decomposition is not None
    assert len(spec.decomposition.sub_parts) == 7
    assert spec.decomposition.path_dag is not None
    assert len(spec.decomposition.path_dag.nodes) == 5
    assert spec.decomposition.fragment_complexity.path_dag_node_count == 5
    assert spec.global_props is None  # lightweight record per Rule 9.17b


def test_roundtrip_parses_again(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    dumped = dumps_litespec(doc)
    reloaded = loads_litespec(dumped)
    assert reloaded.specs[0].id == "mm_search_typed_binder"
    assert len(reloaded.specs[0].decomposition.sub_parts) == 7


def test_loop_analysis(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    loops = doc.specs[0].loop_analysis
    assert loops is not None and len(loops) == 1
    loop = loops[0]
    assert loop.loop_id == "bounded_search_loop"
    assert loop.loop_kind == "for"
    assert loop.desugared_from == "for_c"
    assert loop.iteration_var == "progress"
    assert loop.variant.decreases_on == "iteration"
