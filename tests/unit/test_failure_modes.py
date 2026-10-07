"""Appendix X failure-mode catalogue."""

from litespec.utils.failure_modes import FailureMode, all_failure_modes, failure_mode


def test_enum_value_equals_name():
    assert FailureMode["abi_entry_unbound"].value == "abi_entry_unbound"


def test_catalogue_is_comprehensive():
    modes = all_failure_modes()
    assert len(modes) >= 100
    names = {m.value for m in modes}
    for expected in (
        "abi_entry_unbound",
        "binder_type_annotation_missing",
        "for_c_stage2_undeclared",
        "hash_binding_index_out_of_bounds",
        "path_dag_op_missing",
        "phase_2_dependency_undisclosed",
        "type_identifier_unresolved",
        "variant_synthesis_mode_mismatch",
    ):
        assert expected in names


def test_failure_mode_lookup():
    assert failure_mode("rule_range_citation") is FailureMode["rule_range_citation"]
