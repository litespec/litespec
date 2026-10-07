"""Forward-goto elimination."""

from litespec.lir.effect_expr_ast import (
    Assign,
    BreakLabel,
    Compare,
    Conditional,
    ExprStmt,
    IntLit,
    LabeledBlock,
    Return,
    Sequence,
    Skip,
    Var,
)
from litespec.lowering.goto_elimination import eliminate_gotos


def test_eliminate_gotos_wraps_in_labeled_block():
    effect = Sequence(
        (
            Assign("a", IntLit(1)),
            Conditional(Compare(">", Var("a"), IntLit(0)), Sequence((ExprStmt(Var("__goto_DONE")),)), Skip()),
            ExprStmt(Var("__label_DONE")),
            Assign("b", IntLit(2)),
        )
    )
    result = eliminate_gotos(effect)
    assert isinstance(result, Sequence)
    block = result.items[0]
    assert isinstance(block, LabeledBlock)
    assert block.name == "DONE"
    # goto became break 'DONE
    cond = block.body.items[1]
    assert isinstance(cond, Conditional)
    assert cond.then.items == (BreakLabel("DONE"),)
    # epilogue moved after the block
    assert result.items[1] == Assign("b", IntLit(2))


def test_eliminate_gotos_identity_when_no_labels():
    effect = Sequence((Assign("a", IntLit(1)), Return(Var("a"))))
    assert eliminate_gotos(effect) == effect


def test_eliminate_gotos_no_label_ignores_goto_marker():
    # A goto marker with no label is left untouched (not silently dropped).
    effect = Sequence((ExprStmt(Var("__goto_NOPE")), Assign("a", IntLit(1))))
    assert eliminate_gotos(effect) == effect
