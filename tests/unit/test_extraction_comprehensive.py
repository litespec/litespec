"""Comprehensive extraction tests: more C constructs mapped to LIR."""

from litespec.extraction import extract_function
from litespec.lir.effect_expr_ast import (
    Assign,
    Call,
    Compare,
    Conditional,
    DoWhile,
    Field,
    ForC,
    IntLit,
    Not,
    Return,
    Sequence,
    Var,
)


def test_extract_for_loop_as_for_c():
    c = "unsigned int f(unsigned int n) { unsigned int acc = 0; for (unsigned int i = 0; i < n; i = i + 1) { acc = acc + i; } return acc; }"
    fn = extract_function(c, "f")
    items = fn.effect.items
    assert len(items) == 3
    assert items[0] == Assign("acc", IntLit(0))
    assert isinstance(items[1], ForC)
    assert items[1].name == "i"
    assert items[2] == Return(Var("acc"))


def test_extract_do_while():
    c = "unsigned int f(unsigned int n) { unsigned int x = 0; do { x = x + 1; } while (x < n); return x; }"
    fn = extract_function(c, "f")
    assert isinstance(fn.effect.items[1], DoWhile)


def test_extract_if_else():
    c = "unsigned int f(unsigned int x) { unsigned int r = 0; if (x > 0) { r = 1; } else { r = 0; } return r; }"
    fn = extract_function(c, "f")
    cond = fn.effect.items[1]
    assert isinstance(cond, Conditional)
    assert isinstance(cond.then, Sequence)
    assert isinstance(cond.else_, Sequence)


def test_extract_unary_not():
    c = "unsigned int f(unsigned int x) { unsigned int r = 0; if (!x) { r = 1; } return r; }"
    fn = extract_function(c, "f")
    cond = fn.effect.items[1]
    assert isinstance(cond, Conditional)
    assert isinstance(cond.cond, Not)


def test_extract_call_in_return():
    c = "unsigned int g(unsigned int x) { return x; } unsigned int f(unsigned int x) { return g(x); }"
    fn = extract_function(c, "f")
    assert fn.effect == Return(Call("g", (Var("x"),)))


def test_extract_struct_type_and_pointer_return():
    c = "struct S { unsigned int x; }; struct S *f(struct S *p) { struct S *q = p; return q; }"
    fn = extract_function(c, "f")
    assert fn.return_type == "struct S *"
    assert fn.state_vars == [("q", "S")]  # struct S * → handle type "S"


def test_extract_field_access_and_cast():
    c = (
        "typedef struct B { unsigned int s; struct B *n; } B;"
        "void *f(void *p) { void *r = 0; B *c = (B *)p; if (c->s > 0) { r = c; } return r; }"
    )
    fn = extract_function(c, "f")
    items = fn.effect.items
    assert items[1] == Assign("c", Var("p"))  # cast lowered to identity on the index
    cond = items[2]
    assert isinstance(cond, Conditional)
    assert isinstance(cond.cond, Compare)
    assert cond.cond.left == Field(Var("c"), "s")
