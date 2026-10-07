"""Comprehensive scope-model tests (§7.5.1): fv / bound / substitute across constructors."""

from litespec.lir.effect_expr_ast import (
    Assign,
    BinOp,
    BoolLit,
    Compare,
    Conditional,
    DoWhile,
    ExprStmt,
    ForRange,
    IntLit,
    Iterator,
    Let,
    Quantified,
    Var,
    While,
)


def test_while_fv_bound():
    e = While(Compare("<", Var("i"), Var("n")), Assign("i", BinOp("+", Var("i"), IntLit(1))))
    assert e.fv() == {"i", "n"}
    assert e.bound() == set()


def test_conditional_fv_bound():
    e = Conditional(BoolLit(True), Assign("x", IntLit(1)), Assign("y", IntLit(2)))
    assert e.fv() == {"x", "y"}
    assert e.bound() == set()


def test_for_range_fv_bound():
    e = ForRange("x", "Nat", Var("xs"), Assign("acc", Var("x")))
    assert e.fv() == {"xs", "acc"}  # x is bound
    assert e.bound() == {"x"}


def test_iterator_fv_bound():
    e = Iterator("x", "Nat", Var("xs"), Assign("acc", Var("x")))
    assert e.fv() == {"xs", "acc"}
    assert e.bound() == {"x"}


def test_do_while_fv_bound():
    e = DoWhile(Assign("x", IntLit(1)), Compare("<", Var("x"), IntLit(5)))
    assert e.fv() == {"x"}
    assert e.bound() == set()


def test_quantified_bound_and_body_fv():
    e = Quantified("forall", "v", "Nat", "Nat", Assign("acc", Var("v")))
    assert "v" not in e.fv()  # v is bound
    assert "acc" in e.fv()
    assert e.bound() == {"v"}


def test_let_substitute_non_capture():
    # Let(y, e', C) where C uses a free var x (not the binder y); substituting x
    # must not touch or rename the binder y.
    e = Let("y", "Nat", ExprStmt(IntLit(0)), Assign("z", Var("x")))
    result = e.substitute("x", IntLit(5))
    assert isinstance(result, Let)
    assert result.name == "y"
    assert result.body.expr == IntLit(5)


def test_for_range_substitute_capture_avoiding():
    # for x in E do C; substitute a free var with an expr mentioning x -> rename x.
    e = ForRange("x", "Nat", Var("xs"), Assign("acc", Var("x")))
    result = e.substitute("xs", Var("x"))
    assert isinstance(result, ForRange)
    assert result.name != "x"  # binder renamed to avoid capture
    assert result.name.startswith("x")


def test_quantified_substitute_capture_avoiding():
    e = Quantified("forall", "v", "Nat", "Nat", Assign("acc", Var("v")))
    result = e.substitute("acc", Var("v"))
    assert isinstance(result, Quantified)
    assert result.name != "v"
    assert result.name.startswith("v")


def test_do_while_substitute():
    e = DoWhile(Assign("x", Var("n")), Compare("<", Var("x"), IntLit(5)))
    result = e.substitute("n", IntLit(10))
    assert result.body.expr == IntLit(10)


def test_while_substitute():
    e = While(Compare("<", Var("i"), Var("n")), Assign("i", BinOp("+", Var("i"), IntLit(1))))
    result = e.substitute("n", IntLit(10))
    assert result.cond.right == IntLit(10)
