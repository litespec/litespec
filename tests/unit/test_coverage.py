"""Verification-coverage classification + test auto-generation."""

from litespec.equivalence.coverage import classify_function, coverage_report, format_coverage
from litespec.verification import generate_tests


def test_classify_impure_function_is_structural():
    # a call to an *unported* function (not in the fn table) is impure → structural
    src = "unsigned int f(unsigned int n) { return ext_helper(n); }\n"
    assert classify_function(src, "f") == "structural"


def test_classify_pure_function():
    src = "unsigned int f(unsigned int n) { return n + 1; }"
    level = classify_function(src, "f")
    # pure arithmetic: differential (if clang can compile the harness) else concrete
    assert level in ("differential", "concrete")


def test_classify_calls_ported_pure_function_is_interpretable():
    # inter-function interpretation: f calls the ported pure helper → still interpretable
    src = (
        "unsigned int helper(unsigned int x) { return x + 1; }\nunsigned int f(unsigned int n) { return helper(n); }\n"
    )
    assert classify_function(src, "f") in ("differential", "concrete")


def test_coverage_report_sums_to_total():
    src = "unsigned int f(unsigned int n) { return n + 1; }\nunsigned int g(unsigned int n) { return ext_helper(n); }\n"
    counts, per_fn = coverage_report(src, ["f", "g"])
    assert sum(counts.values()) == 2
    assert per_fn["g"] == "structural"
    assert "structural" in format_coverage(counts, 2)


def test_generate_tests_emits_parametrized_module():
    text = generate_tests("/tmp/x.c", ["f", "g"])
    assert "test_each_function_is_verified" in text
    assert "test_coverage_has_no_mismatches" in text
    assert "'f'," in text and "'g'," in text
    assert "verify_function" in text


def test_verify_command_end_to_end(tmp_path):
    import shutil

    import pytest

    if shutil.which("rustc") is None:
        pytest.skip("rustc not available")
    from litespec.cli.verify_command import verify_command

    src = tmp_path / "t.c"
    src.write_text("unsigned int f(unsigned int n) { return n + 1; }\n", encoding="utf-8")
    assert verify_command([str(src)]) == 0
