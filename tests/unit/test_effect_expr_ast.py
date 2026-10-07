"""frozen EffectExpr AST, scope model, and the effect parser (§7.5)."""

from litespec.lir.effect_expr_ast import (
    Assign,
    BinOp,
    Call,
    Compare,
    ExprStmt,
    ForC,
    IntLit,
    Let,
    Var,
)
from litespec.lir.parser import parse_effect

_EFFECT = """\
for progress:Nat = 0; progress < limit; progress' = progress + 1 do
  cursor' = advance_cursor(cursor)
od
"""


def test_parse_for_c():
    node = parse_effect(_EFFECT)
    assert isinstance(node, ForC)
    assert node.name == "progress"
    assert node.type == "Nat"
    assert isinstance(node.init, ExprStmt)
    assert node.init.expr == IntLit(0)
    assert isinstance(node.guard, Compare)
    assert node.guard.op == "<"
    assert isinstance(node.step, Assign)
    assert node.step.target == Var("progress")
    assert isinstance(node.body, Assign)
    assert node.body.target == Var("cursor")
    assert isinstance(node.body.expr, Call)
    assert node.body.expr.name == "advance_cursor"


def test_for_c_scope_model():
    node = parse_effect(_EFFECT)
    fv = node.fv()
    assert fv == {"limit", "cursor", "advance_cursor"}
    assert node.bound() == {"progress"}


def test_parse_sequence_and_while():
    node = parse_effect("seq { x' = 1; while x < 10 do x' = x + 1 od }")
    from litespec.lir.effect_expr_ast import Sequence, While

    assert isinstance(node, Sequence)
    assert len(node.items) == 2
    assert isinstance(node.items[1], While)


def test_let_capture_avoiding_substitution():
    # Let(y, e', C) with y ∈ fv(substitute-expression) triggers α-renaming.
    node = Let("y", "Nat", ExprStmt(IntLit(0)), ExprStmt(Var("y")))
    # substitute x := y into the body; y is free in e, so y is renamed.
    result = node.substitute("x", Var("y"))
    assert isinstance(result, Let)
    assert result.name != "y"
    assert result.name.startswith("y")


def test_substitute_non_capture():
    node = Let("y", "Nat", ExprStmt(IntLit(0)), ExprStmt(BinOp("+", Var("y"), Var("x"))))
    result = node.substitute("x", IntLit(5))
    assert result.body.expr.right == IntLit(5)


def test_parse_bare_assign_and_skip():
    from litespec.lir.effect_expr_ast import Skip

    assert isinstance(parse_effect("skip"), Skip)
    assert parse_effect("x' = 42") == Assign("x", IntLit(42))
