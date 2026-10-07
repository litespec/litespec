"""C→LIR extraction (tree-sitter-c)."""

from litespec.extraction import collect_loop_analyses, extract_function
from litespec.lir.effect_expr_ast import (
    Assign,
    Compare,
    Conditional,
    Field,
    IntLit,
    Return,
    Sequence,
    Var,
    While,
)

_C_SOURCE = """\
typedef struct Block { unsigned int size; struct Block *next; } Block;

void *LOS_MemAlloc(void *pool, unsigned int size) {
    void *result = 0;
    Block *cursor = (Block *)pool;
    while (cursor->size < size) {
        cursor = cursor->next;
    }
    if (cursor->size >= size) {
        result = cursor;
    }
    return result;
}
"""


def test_extract_function_effect():
    fn = extract_function(_C_SOURCE, "LOS_MemAlloc")
    assert fn.name == "LOS_MemAlloc"
    assert "void" in fn.return_type

    effect = fn.effect
    assert isinstance(effect, Sequence)
    items = list(effect.items)
    assert len(items) == 5

    # void *result = 0  ->  result := 0
    assert items[0] == Assign("result", IntLit(0))
    # Block *cursor = (Block *)pool  ->  cursor := pool
    assert items[1] == Assign("cursor", Var("pool"))
    # while (cursor->size < size) { cursor = cursor->next; }
    assert isinstance(items[2], While)
    assert items[2].cond == Compare("<", Field(Var("cursor"), "size"), Var("size"))
    assert list(items[2].body.items) == [Assign("cursor", Field(Var("cursor"), "next"))]
    # if (cursor->size >= size) { result = cursor; }
    assert isinstance(items[3], Conditional)
    assert items[3].cond == Compare(">=", Field(Var("cursor"), "size"), Var("size"))
    assert list(items[3].then.items) == [Assign("result", Var("cursor"))]
    # return result;
    assert items[4] == Return(Var("result"))


def test_extract_state_vars():
    fn = extract_function(_C_SOURCE, "LOS_MemAlloc")
    names = {name for name, _ in fn.state_vars}
    assert names == {"result", "cursor"}


def test_extract_loop_analysis():
    fn = extract_function(_C_SOURCE, "LOS_MemAlloc")
    loops = collect_loop_analyses(fn.effect, "LOS_MemAlloc")
    assert len(loops) == 1
    assert loops[0].loop_kind == "while"
    assert loops[0].function == "LOS_MemAlloc"


def test_extract_function_missing():
    import pytest

    with pytest.raises(ValueError):
        extract_function(_C_SOURCE, "nope")
