"""Negative-test catalogue (conformance tests; Volume 2 Appendix X).

Each negative test is a conformance test: the toolchain must produce the declared
failure mode on the declared input. These tests (a) verify the ``FailureMode``
enum covers the normative catalogue identifiers, and (b) exercise a representative
subset of the well-formedness negative tests end-to-end.
"""

from __future__ import annotations

from litespec.lir.wellformedness import check_wellformedness
from litespec.serialization import loads_litespec
from litespec.utils.failure_modes import FailureMode

#: Normative failure-mode identifiers from the negative-test catalogue that the
#: ``FailureMode`` enum must cover.
_CATALOGUE_FAILURE_MODES = [
    "duplicate_rule_definition",
    "loop_optimization_schema_mismatch",
    "loop_optimization_certificates_orphaned",
    "lir_spec_loop_analysis_missing",
    "lir_spec_field_access_violation",
    "pipeline_fold_state_erasure",
    "schema_type_undefined",
    "helper_arity_mismatch",
    "rule_range_citation",
    "control_flow_token_incomplete",
    "stutter_encoding_undeclared",
    "d67_path_condition_wrong_segment",
    "path_dag_op_missing",
    "hash_binding_index_out_of_bounds",
    "for_c_stage2_undeclared",
    "for_c_init_lost",
    "type_identifier_unresolved",
    "helper_definition_missing",
    "dependency_scan_unrecorded",
    "hoare_decomposition_not_recursive",
    "phase_2_dependency_undisclosed",
    "resolve_target_ambiguous",
    "typing_context_leaked_to_ir",
    "expression_type_ambiguous",
    "variant_synthesis_mode_mismatch",
    "indicator_naming_noncanonical",
]


def _minimal_document(**overrides) -> str:
    doc = {
        "litespec_version": "0.28.3",
        "profile": {"name": "litespec-liteos", "version": "1.0.0"},
        "module": {
            "name": "kernel_mm",
            "display_name": "Kernel Memory Management",
            "phase": "lightweight",
            "module_type": "kernel",
            "source_repo": "https://gitee.com/openharmony/kernel_liteos_a",
            "source_commit": "1b5d3de13bea4a93e6713f180710f2f307cad403",
            "extraction_timestamp": "2025-01-01T00:00:00Z",
            "extractor": "litespec-extractor",
        },
        "specs": [
            {
                "id": "spec_1",
                "title": "spec",
                "category": "requirement",
                "priority": "high",
                "source": {"file": "f.c", "function": "f"},
                "contract": {"preconditions": [], "postconditions": [], "invariants": []},
            }
        ],
    }
    doc.update(overrides)
    import yaml

    return yaml.safe_dump(doc, sort_keys=False)


def test_failure_mode_enum_covers_catalogue():
    names = {m.value for m in FailureMode}
    missing = [m for m in _CATALOGUE_FAILURE_MODES if m not in names]
    assert not missing, f"FailureMode enum missing catalogue identifiers: {missing}"


def test_hash_binding_index_out_of_bounds():
    # A $hash_bindings.5 reference with only 1 binding → WF84 index-out-of-bounds.
    doc = loads_litespec(
        _minimal_document(
            specs=[
                {
                    "id": "spec_1",
                    "title": "uses $hash_bindings.5",
                    "category": "requirement",
                    "priority": "high",
                    "source": {"file": "f.c", "function": "f"},
                    "contract": {"preconditions": [], "postconditions": [], "invariants": []},
                }
            ],
            hash_bindings={"bindings": [{"field": "f0"}]},
        )
    )
    report = check_wellformedness(doc)
    modes = [f.failure_mode for f in report.failures]
    assert "hash_binding_index_out_of_bounds" in modes, modes


def test_wellformed_document_has_no_failures():
    doc = loads_litespec(_minimal_document())
    report = check_wellformedness(doc)
    assert not report.failures, [f.failure_mode for f in report.failures]
