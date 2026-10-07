"""LIR→Rust lowering (structural)."""

from litespec.extraction import extract_function
from litespec.lir.effect_expr_ast import BinOp, Compare, Var
from litespec.lowering import emit_module, render_expr_rust
from litespec.lowering.port_module import port_module

_C = """\
unsigned int sum_to(unsigned int n) {
    unsigned int acc = 0;
    unsigned int i = 0;
    while (i < n) {
        acc = acc + i;
        i = i + 1;
    }
    return acc;
}
"""


def test_render_expr_rust_operators():
    # C `&&`/`||`/`==` yield an integer 0/1 (not a Rust bool) in value position.
    assert render_expr_rust(BinOp("and", Var("a"), Var("b"))) == "(((a) != 0) && ((b) != 0)) as u64"
    assert render_expr_rust(BinOp("or", Var("a"), Var("b"))) == "(((a) != 0) || ((b) != 0)) as u64"
    assert render_expr_rust(Compare("=", Var("a"), Var("b"))) == "((a) == (b)) as u64"


def test_emit_module_structure():
    fn = extract_function(_C, "sum_to")
    rust = emit_module("sum_to", [("n", "Nat")], "Nat", fn.state_vars, fn.effect)

    assert "fn sum_to(n: u64) -> u64" in rust
    assert "let mut acc: u64 = 0;" in rust
    assert "let mut i: u64 = 0;" in rust
    assert "while i < n {" in rust
    assert "return acc;" in rust


def test_port_module_wraps_in_module_name():
    rust = port_module(b"unsigned int f(unsigned int x) { return x + 1; }", ["f"], module_name="rliteos")
    assert rust.startswith("pub mod rliteos {\n")
    assert rust.rstrip().endswith("}")
    assert "pub unsafe fn f(" in rust


def test_addr_of_local_output_param():
    # &local (address-of a local) allocates the local in the flat memory model.
    src = b"""
typedef unsigned int UINT32;
#define LOS_OK 0
UINT32 f(UINT32 *out) { *out = 42; return LOS_OK; }
UINT32 g(void) { UINT32 x = 0; f(&x); return x; }
"""
    rust = port_module(src, ["f", "g"], module_name="")
    # the address-taken local `x` is stored in a MEM slot and read/written through it
    assert "__write(32768, 0);" in rust  # x = 0
    assert "f(32768);" in rust  # f(&x)
    assert "__read(32768)" in rust  # return x
