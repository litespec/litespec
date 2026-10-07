"""Rust verification backend adapters."""

from litespec.backends import all_backends, backend_names, dispatch, get_backend


def test_backend_names():
    assert backend_names() == ["verus", "kani", "smack", "rem", "creusot"]


def test_each_backend_discharges_trivial():
    for backend in all_backends():
        result = backend.discharge_trivial()
        assert result.status == "pass"
        assert result.ok


def test_verify_trivial_obligation():
    for backend in all_backends():
        result = backend.verify("x + 0 = x")
        assert result.status == "pass"


def test_verify_nontrivial_reports_warn():
    result = get_backend("verus").verify("x + y = y + x")
    assert result.status == "warn"


def test_dispatch():
    assert dispatch("x = x", "kani").status == "pass"
    assert dispatch("0 + x = x", "creusot").status == "pass"


def test_unknown_backend():
    import pytest

    with pytest.raises(KeyError):
        get_backend("nope")
