"""Verus + Kani annotation synthesis."""

from litespec.annotation import (
    derive_unwind_bound,
    synthesize_decreases,
    synthesize_ensures,
    synthesize_invariants,
    synthesize_kani_harness,
    synthesize_requires,
    synthesize_verus_function,
)
from litespec.lir.parser import parse_effect
from litespec.schema.contract_layer import ContractLayer, LoopInvariantClause
from litespec.schema.loop_analysis import BoundedIteration, LoopAnalysis, LoopVariant
from litespec.schema.primitives import LIRNodeRef, Predicate


def _contract() -> ContractLayer:
    return ContractLayer(
        preconditions=[Predicate(expression="n > 0", description="n positive")],
        postconditions=[Predicate(expression="result >= 0", description="nonnegative")],
        loop_invariants=[LoopInvariantClause(family="boundary", expr="i <= n", scope="all")],
    )


def _loop() -> LoopAnalysis:
    return LoopAnalysis(
        loop_id="L",
        function="sum_to",
        lir_fragment=LIRNodeRef(function="sum_to", node_id="L"),
        loop_kind="while",
        bound=BoundedIteration(target="i", kind="loop", bound=256, bound_source="config_param", on_exceed="assert"),
        variant=LoopVariant(
            expr="lambda sigma. n - sigma.i", domain="Nat", decreases_on="iteration", well_founded="proved"
        ),
    )


def test_synthesize_requires_ensures_invariants():
    c = _contract()
    assert synthesize_requires(c) == ["requires n > 0"]
    assert synthesize_ensures(c) == ["ensures result >= 0"]
    assert synthesize_invariants(c) == ["invariant i <= n"]


def test_synthesize_decreases():
    assert synthesize_decreases([_loop()]) == ["decreases lambda sigma. n - sigma.i"]


def test_derive_unwind_bound():
    assert derive_unwind_bound([_loop()]) == 256
    assert derive_unwind_bound([]) == 1


def test_synthesize_kani_harness():
    harness = synthesize_kani_harness("sum_to", _contract(), 256)
    assert "#[kani::proof]" in harness
    assert "#[kani::unwind(256)]" in harness
    assert "kani::assume(n > 0);" in harness
    assert "kani::assert(result >= 0);" in harness


def test_synthesize_verus_function():
    effect = parse_effect("seq { i' = 0; while i < n do seq { i' = i + 1 } od }")
    verus = synthesize_verus_function("sum_to", [("n", "Nat")], "Nat", [("i", "Nat")], effect, _contract(), [_loop()])
    assert "verus! {" in verus
    assert "requires n > 0" in verus
    assert "ensures result >= 0" in verus
    assert "invariant i <= n" in verus
    assert "decreases lambda sigma. n - sigma.i" in verus
