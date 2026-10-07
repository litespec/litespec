"""rule registry decorators."""

from litespec.rules import derivation_rule, registry, rule


def test_rule_registration():
    @rule("R79", "N", section="§5.2", failure_mode="abi_entry_unbound")
    def abi_entry_coverage(spec):
        return True

    r = registry.get("R79")
    assert r is not None
    assert r.classification == "N"
    assert r.section == "§5.2"
    assert r.failure_mode == "abi_entry_unbound"
    assert not r.is_derivation


def test_derivation_rule_registration():
    @derivation_rule("D1", "N", section="§13")
    def derive_spec_id(spec):
        return spec.id

    r = registry.get("D1")
    assert r is not None
    assert r.is_derivation


def test_by_classification():
    norms = registry.by_classification("N")
    assert any(r.id == "R79" for r in norms)
