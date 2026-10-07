"""conformance criteria and completeness checks."""

from pathlib import Path

from litespec.serialization import load_litespec
from litespec.validation import (
    CONFORMANCE_CRITERIA,
    check_conformance,
    check_ec_completeness,
    check_isir_completeness,
    check_placeholders,
)


def test_conformance_criteria_count():
    assert len(CONFORMANCE_CRITERIA) == 84
    assert CONFORMANCE_CRITERIA[1].startswith("Supports every")
    assert CONFORMANCE_CRITERIA[84].startswith("Enforces the D74")


def test_example_passes_conformance(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    report = check_conformance(doc)
    assert report.ok, report.failures


def test_example_passes_placeholder_check(mm_search_typed_binder_path):
    doc = load_litespec(mm_search_typed_binder_path)
    assert check_placeholders(doc).ok


def test_ec_completeness():
    # No artifacts → all five seams present but not discharged (warn, not pass).
    result = check_ec_completeness()
    assert result.status == "warn"
    assert len(result.warnings) == 5


def test_isir_completeness():
    isir_base = Path(__file__).resolve().parents[2] / "targets" / "rliteos" / "spec"
    result = check_isir_completeness({"kernel_mm": ["LOS_MemAlloc", "LOS_MemFree"]}, isir_base)
    assert result.ok


def test_isir_completeness_detects_missing():
    isir_base = Path(__file__).resolve().parents[2] / "targets" / "rliteos" / "spec"
    result = check_isir_completeness({"kernel_mm": ["LOS_MemAlloc", "nope"]}, isir_base)
    assert not result.ok
