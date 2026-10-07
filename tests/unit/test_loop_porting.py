"""Loop porting refinements: for-loop init/step, goto/label, struct types, field access."""

from litespec.extraction import extract_function
from litespec.extraction.type_modeling import c_return_to_type_expr
from litespec.lir.effect_expr_ast import (
    Assign,
    BinOp,
    Conditional,
    ExprStmt,
    Field,
    ForC,
    Index,
    IntLit,
    Return,
    Var,
)


def test_for_loop_pointer_init_and_step_are_assigns():
    c = (
        "struct N { unsigned int v; struct N *next; };"
        "struct N *find(struct N *head, unsigned int k) {"
        "  struct N *node = 0;"
        "  for (node = head; node != 0; node = node->next) { if (node->v == k) return node; }"
        "  return 0;"
        "}"
    )
    fn = extract_function(c, "find")
    items = fn.effect.items
    assert items[0] == Assign("node", IntLit(0))
    forc = items[1]
    assert isinstance(forc, ForC)
    assert forc.name == "node"  # binder extracted from the assignment target
    assert forc.init == Assign("node", Var("head"))
    assert forc.step == Assign("node", Field(Var("node"), "next"))  # -> modeled as Field


def test_for_loop_compound_step():
    c = "unsigned int f(unsigned int n) { unsigned int s = 0; for (unsigned int i = 0; i < n; i += 2) { s = s + i; } return s; }"
    fn = extract_function(c, "f")
    forc = fn.effect.items[1]
    assert isinstance(forc, ForC)
    assert forc.step == Assign("i", BinOp("+", Var("i"), IntLit(2)))


def test_for_loop_declaration_init_binder():
    c = "unsigned int f(unsigned int n) { unsigned int s = 0; for (unsigned int i = 0; i < n; i = i + 1) { s = s + i; } return s; }"
    fn = extract_function(c, "f")
    forc = fn.effect.items[1]
    assert forc.name == "i"
    assert forc.init == Assign("i", IntLit(0))
    assert forc.step == Assign("i", BinOp("+", Var("i"), IntLit(1)))


def test_goto_and_label_map_to_placeholders():
    c = "int f(int x) { if (x > 0) goto DONE; return 0; DONE: return 1; }"
    fn = extract_function(c, "f")
    items = fn.effect.items
    assert len(items) == 4
    assert isinstance(items[0], Conditional)
    assert items[0].then.items[0] == ExprStmt(Var("__goto_DONE"))
    assert items[1] == Return(IntLit(0))
    assert items[2] == ExprStmt(Var("__label_DONE"))
    assert items[3] == Return(IntLit(1))


def test_field_access_normalized_to_dots():
    c = "struct S { unsigned int a; unsigned int b; }; unsigned int f(struct S *p) { return p->a + p->b; }"
    fn = extract_function(c, "f")
    assert fn.effect == Return(BinOp("+", Field(Var("p"), "a"), Field(Var("p"), "b")))


def test_struct_return_type_prefix_stripped():
    c = "struct S { unsigned int x; }; struct S *f(void) { return 0; }"
    fn = extract_function(c, "f")
    assert c_return_to_type_expr(fn.return_type) == "S"


def test_else_clause_is_mapped():
    c = "unsigned int f(unsigned int x) { unsigned int r; if (x > 0) { r = 1; } else { r = 2; } return r; }"
    fn = extract_function(c, "f")
    cond = fn.effect.items[0]
    assert isinstance(cond, Conditional)
    assert list(cond.then.items) == [Assign("r", IntLit(1))]
    assert list(cond.else_.items) == [Assign("r", IntLit(2))]  # else body not dropped


def test_uninitialized_locals_collected():
    c = "unsigned int f(unsigned int n) { unsigned int index, tmp; unsigned int mask; index = n; return index; }"
    fn = extract_function(c, "f")
    names = {n for n, _ in fn.state_vars}
    assert {"index", "tmp", "mask"} <= names


def test_index_produces_index_node():
    c = "unsigned int f(unsigned int *arr, unsigned int i) { return arr[i]; }"
    fn = extract_function(c, "f")
    assert fn.effect == Return(Index(Var("arr"), Var("i")))
