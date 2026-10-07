"""Macro extraction + resolution."""

from litespec.extraction import extract_function, parse_c
from litespec.extraction.macro_table import MacroTable
from litespec.lir.effect_expr_ast import BinOp, Compare, Conditional, IntLit, Return, Var

_SRC = """\
#define SIZE 128
#define SHIFT 3
#define MASK 0x80000000U
#define IDX(x) ((x) >> SHIFT)
#define FLAG(x) ((x) & MASK)
unsigned int f(unsigned int i) {
    if (i < SIZE) { return IDX(i); }
    return FLAG(i);
}
"""


def test_macro_table_extracts():
    tu = parse_c(_SRC.encode())
    m = MacroTable.from_translation_unit(tu)
    assert m.constants["SIZE"] == "128"
    assert m.constants["MASK"] == "0x80000000U"
    assert m.functions["IDX"] == (("x",), "((x) >> SHIFT)")
    assert m.functions["FLAG"] == (("x",), "((x) & MASK)")


def test_resolve_constants_and_function_macros():
    fn = extract_function(_SRC, "f")
    items = fn.effect.items
    assert isinstance(items[0], Conditional)
    # i < SIZE → i < 128
    assert items[0].cond == Compare("<", Var("i"), IntLit(128))
    # return IDX(i) → return (i >> 3)
    assert items[0].then.items[0] == Return(BinOp(">>", Var("i"), IntLit(3)))
    # return FLAG(i) → return (i & 0x80000000)
    assert items[1] == Return(BinOp("&", Var("i"), IntLit(0x80000000)))


def test_nested_constant_resolution():
    c = (
        "#define A 31\n"
        "#define B 24\n"
        "#define S 3\n"
        "#define C (A + (B << S))\n"
        "unsigned int f(unsigned int x) { return C; }\n"
    )
    fn = extract_function(c, "f")
    # C = 31 + (24 << 3) = 223, folded to a constant
    assert fn.effect == Return(IntLit(223))
