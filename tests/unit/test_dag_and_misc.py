"""Comprehensive path-DAG, progressive-lowering, and misc unit tests."""

import pytest

from litespec.abstraction import derive_stutter_encoding
from litespec.derivation.progressive_lowering import progressive_lower
from litespec.equivalence.counterexample import Counterexample
from litespec.equivalence.counterexample_minimization import minimize
from litespec.equivalence.dispatch import dispatch
from litespec.equivalence.observation_spaces import ObservationSpace
from litespec.equivalence.relations import discharge
from litespec.lir.effect_expr_ast import Call, CallEffect, Sequence, Var, While
from litespec.lir.parser import parse_effect
from litespec.pathdag import build_path_dag
from litespec.pipeline.pipeline_state import CheckResult
from litespec.schema.loop_analysis import LoopAnalysis, LoopVariant
from litespec.schema.primitives import LIRNodeRef


def test_dag_conditional_branches():
    dag = build_path_dag(parse_effect("if x < 10 then y' = 1 else y' = 2"), "d")
    assert [str(n.kind) for n in dag.nodes] == ["entry", "branch_then", "branch_else"]


def test_dag_return_node():
    dag = build_path_dag(parse_effect("return x"), "d")
    assert [str(n.kind) for n in dag.nodes] == ["entry", "return"]


def test_dag_while_body_with_return():
    dag = build_path_dag(parse_effect("while x < 10 do seq { if x > 5 then return x else skip } od"), "d")
    kinds = [str(n.kind) for n in dag.nodes]
    assert "loop_body" in kinds and "loop_exit" in kinds and "return" in kinds


def test_progressive_lower_for_range():
    e = parse_effect("for x : Nat in xs do acc' = x od")
    lowered = progressive_lower(e)
    assert isinstance(lowered, Sequence)
    assert lowered.items[0] == CallEffect("MakeIterator", (Var("x"),))
    assert isinstance(lowered.items[1], While)
    assert lowered.items[1].cond == Call("has_next", (Var("x"),))


def test_stutter_encoding_iteration_returns_none():
    loop = LoopAnalysis(
        loop_id="L",
        function="f",
        lir_fragment=LIRNodeRef(function="f", node_id="L"),
        loop_kind="while",
        variant=LoopVariant(expr="w", domain="Nat", decreases_on="iteration", well_founded="proved"),
    )
    assert derive_stutter_encoding(loop) is None


def test_stutter_encoding_stutter():
    loop = LoopAnalysis(
        loop_id="L",
        function="f",
        lir_fragment=LIRNodeRef(function="f", node_id="L"),
        loop_kind="while",
        variant=LoopVariant(expr="w", domain="Nat", decreases_on="stutter", well_founded="proved"),
    )
    assert derive_stutter_encoding(loop) == {"kind": "descent_through_alpha", "rank_witness_hash": "0" * 64}


def test_counterexample_minimize_identity():
    ce = Counterexample(kind="lir_to_isir", trace=((1, 2),))
    assert minimize(ce) == ce


def test_observation_space_membership():
    space = ObservationSpace(ports=("a",), observables=("o",))
    assert "o" in space and "z" not in space


def test_relations_discharge():
    assert discharge("exact", "refinement_only") is True
    assert discharge("refinement_only", "exact") is False


def test_dispatch_unknown_seam():
    with pytest.raises(KeyError):
        dispatch("nope")


def test_check_result_monoid_combine():
    a = CheckResult(status="warn", warnings=["w"])
    b = CheckResult(status="fail", errors=["e"])
    combined = a.combine(b)
    assert combined.status == "fail"
    assert combined.errors == ["e"]
    assert combined.warnings == ["w"]
