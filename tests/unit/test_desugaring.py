"""D84 ForC desugaring and D77 loop-construct desugaring."""

from litespec.derivation.for_c_desugaring import derive_for_c_desugaring
from litespec.derivation.progressive_lowering import derive_loop_construct_desugaring, progressive_lower
from litespec.lir.effect_expr_ast import (
    Assign,
    BinOp,
    Call,
    Compare,
    DoWhile,
    ExprStmt,
    ForC,
    IntLit,
    Sequence,
    Var,
    While,
)
from litespec.lir.parser import parse_effect

_EFFECT = """\
for progress:Nat = 0; progress < limit; progress' = progress + 1 do
  cursor' = advance_cursor(cursor)
od
"""


def test_d84_desugars_for_c_to_sequence_while():
    node = parse_effect(_EFFECT)
    assert isinstance(node, ForC)
    result = derive_for_c_desugaring(node)

    assert isinstance(result, Sequence)
    assert len(result.items) == 2
    init, loop = result.items
    assert isinstance(init, ExprStmt)
    assert init.expr == IntLit(0)
    assert isinstance(loop, While)
    assert loop.cond == Compare("<", Var("progress"), Var("limit"))
    assert isinstance(loop.body, Sequence)
    body, step = loop.body.items
    assert body == Assign("cursor", Call("advance_cursor", (Var("cursor"),)))
    assert step == Assign("progress", BinOp("+", Var("progress"), IntLit(1)))


def test_d77_retains_for_c():
    node = parse_effect(_EFFECT)
    lowered = progressive_lower(node)
    assert isinstance(lowered, ForC)  # retained as a Stage-2 construct


def test_d77_dowhile():
    node = parse_effect("do x' = 1 while x < 5 od")
    assert isinstance(node, DoWhile)
    result, _ = derive_loop_construct_desugaring(node)
    assert isinstance(result, Sequence)
    assert len(result.items) == 2
    assert isinstance(result.items[1], While)


def test_d77_dowhile_full_pipeline():
    node = parse_effect("do x' = 1 while x < 5 od")
    lowered = progressive_lower(node)
    # do x'=1 while x<5 od  ->  seq { x'=1; while x<5 do x'=1 od }
    assert isinstance(lowered, Sequence)
    assert isinstance(lowered.items[1], While)
