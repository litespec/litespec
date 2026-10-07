"""Comprehensive parser tests: every EffectExpr constructor (§7.5)."""

from litespec.lir.effect_expr_ast import (
    Assign,
    CallEffect,
    Conditional,
    DoWhile,
    ExprStmt,
    ForC,
    ForRange,
    Guard,
    IntLit,
    Iterator,
    Let,
    Quantified,
    Return,
    Sequence,
    SetUpdate,
    Skip,
    Var,
)
from litespec.lir.parser import parse_effect


def test_parse_conditional():
    e = parse_effect("if x < 10 then y' = 1 else y' = 2")
    assert isinstance(e, Conditional)
    assert e.then == Assign("y", IntLit(1))
    assert e.else_ == Assign("y", IntLit(2))


def test_parse_let():
    e = parse_effect("let z : Nat = skip in z' = 1")
    assert isinstance(e, Let)
    assert e.name == "z" and e.type == "Nat"
    assert isinstance(e.value, Skip)
    assert e.body == Assign("z", IntLit(1))


def test_parse_quantified():
    e = parse_effect("forall v : Nat in Nat, v' = v")
    assert isinstance(e, Quantified)
    assert e.quantifier == "forall" and e.name == "v"


def test_parse_call_effect():
    e = parse_effect("call foo(1, x)")
    assert e == CallEffect("foo", (IntLit(1), Var("x")))


def test_parse_guard():
    e = parse_effect("guard x < 10")
    assert isinstance(e, Guard)


def test_parse_return_with_and_without_arg():
    assert parse_effect("return x") == Return(Var("x"))
    assert parse_effect("return") == Return(None)


def test_parse_for_range():
    e = parse_effect("for x : Nat in xs do x' = x od")
    assert isinstance(e, ForRange)
    assert e.name == "x"


def test_parse_do_while():
    e = parse_effect("do x' = 1 while x < 5 od")
    assert isinstance(e, DoWhile)


def test_parse_iterator():
    e = parse_effect("iterator x : Nat in xs do x' = x od")
    assert isinstance(e, Iterator)


def test_parse_set_update():
    e = parse_effect("x' = (y \\ {z}) ∪ {w}")
    assert isinstance(e, SetUpdate)
    assert e.target == "x" and e.source == "y"


def test_parse_for_c():
    e = parse_effect("for i : Nat = 0; i < n; i' = i + 1 do acc' = acc + i od")
    assert isinstance(e, ForC)
    assert e.name == "i"
    assert isinstance(e.init, ExprStmt)


def test_parse_sequence_empty_and_single():
    assert isinstance(parse_effect("seq { }"), Sequence)
    assert isinstance(parse_effect("seq { x' = 1 }"), Sequence)
