"""ISIR emission, validation, client, and result parsing."""

from litespec.interscope.config import interscope_root
from litespec.interscope.isir import effect_to_actions, emit_isir_module, render_isir_expr, validate_isir
from litespec.interscope.results import parse_proof_result
from litespec.lir.effect_expr_ast import Compare, IntLit, Var
from litespec.lir.parser import parse_effect
from litespec.schema.contract_layer import ContractLayer
from litespec.schema.primitives import Predicate


def _contract() -> ContractLayer:
    return ContractLayer(
        preconditions=[Predicate(expression="n > 0", description="n positive")],
        postconditions=[Predicate(expression="result >= 0", description="nonnegative")],
    )


def test_emit_and_validate_isir():
    effect = parse_effect("seq { acc' = 0; i' = 0 }")
    isir = emit_isir_module("sum_to", [("acc", "Nat"), ("i", "Nat")], effect, _contract())

    assert isir["isir_version"] == "0.1"
    assert isir["module"]["name"] == "sum_to"
    assert len(isir["module"]["clocks"]) == 1
    assert len(isir["module"]["resets"]) == 1
    assert [s["name"] for s in isir["module"]["state"]] == ["acc", "i"]
    assert len(isir["module"]["rules"]) == 1
    assert validate_isir(isir).ok


def test_emit_with_params_inputs():
    effect = parse_effect("seq { acc' = 0 }")
    isir = emit_isir_module("sum_to", [("acc", "Nat")], effect, params=[("n", "Nat")])
    assert isir["module"]["inputs"] == [{"name": "n", "direction": "input", "type": "bits<32>"}]


def test_validate_isir_rejects_missing_module():
    assert not validate_isir({"isir_version": "0.1"}).ok


def test_effect_to_actions():
    effect = parse_effect("seq { acc' = 0; i' = acc + 1 }")
    assert effect_to_actions(effect) == ["(write acc 0)", "(write i (add (read acc) 1))"]


def test_effect_to_actions_flattens_loop_body():
    effect = parse_effect("seq { acc' = 0; while i < n do acc' = acc + i od }")
    actions = effect_to_actions(effect)
    assert "(write acc 0)" in actions
    assert "(write acc (add (read acc) (read i)))" in actions  # loop body must be emitted


def test_effect_to_actions_flattens_conditional():
    effect = parse_effect("if x < 0 then y' = 1 else y' = 2")
    actions = effect_to_actions(effect)
    assert "(write y 1)" in actions and "(write y 2)" in actions


def test_render_isir_expr():
    assert render_isir_expr(Compare("<", Var("i"), Var("n"))) == "(lt (read i) (read n))"
    assert render_isir_expr(IntLit(0)) == "0"


def test_parse_proof_result():
    assert parse_proof_result("obligation proved").ok
    assert parse_proof_result("counterexample found").status == "fail"


def test_interscope_root():
    assert interscope_root().endswith("/third_party/interscope")
