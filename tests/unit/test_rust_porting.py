"""Rust porting fixes: NULL, param reassignment, break, stub scaffold."""

from litespec.extraction import extract_function
from litespec.extraction.type_modeling import c_param_to_type_expr
from litespec.lir.effect_expr_ast import (
    Assign,
    BinOp,
    Call,
    CallEffect,
    Compare,
    Conditional,
    ExprStmt,
    IntLit,
    Return,
    Sequence,
    Skip,
    Var,
)
from litespec.lowering import emit_module
from litespec.lowering.effect_expr_to_rust import assigned_targets, render_effect_rust
from litespec.lowering.stub_scaffold import collect_external_symbols, render_stub_scaffold


def test_null_maps_to_zero():
    fn = extract_function("unsigned int f(unsigned int p) { return (p == NULL); }", "f")
    assert isinstance(fn.effect, Return)
    assert fn.effect.expr == Compare("=", Var("p"), IntLit(0))


def test_param_reassignment_uses_mut_not_shadow():
    fn = extract_function("void f(unsigned int size) { size = 5; }", "f")
    params = [(n, c_param_to_type_expr(t, n)) for n, t in fn.parameters]
    rust = emit_module("f", params, "Unit", fn.state_vars, fn.effect)
    assert "mut size: u64" in rust  # param marked mut
    assert "size = 5;" in rust  # reassign, not a shadowing let
    assert "let mut size" not in rust


def test_break_renders_as_break():
    assert render_effect_rust(ExprStmt(Var("__break__")), {}) == "break;"
    assert render_effect_rust(ExprStmt(Var("__continue__")), {}) == "continue;"


def test_assigned_targets_collects_params_and_locals():
    effect = Sequence([Assign("size", IntLit(1)), Assign("acc", IntLit(2))])
    assert assigned_targets(effect) == {"size", "acc"}


def test_stub_scaffold_collects_and_renders():
    effect = Sequence(
        [
            CallEffect("MEM_LOCK", (Var("poolHead"), Var("intSave"))),
            Assign("ptr", Call("OsMemAlloc", (Var("poolHead"), Var("size"), Var("intSave")))),
            Conditional(Call("FLAG", (Var("size"),)), Skip(), Skip()),
        ]
    )
    params = [("pool", "Nat"), ("size", "Nat")]
    state_vars = [("poolHead", "OsMemPoolHead"), ("ptr", "Nat"), ("intSave", "Nat")]

    unknown_types, functions, constants, _fn_ptrs = collect_external_symbols(effect, params, state_vars, "Nat")
    assert unknown_types == {"OsMemPoolHead"}
    assert functions == {
        "MEM_LOCK": (2, "()", False),
        "OsMemAlloc": (3, "u64", False),
        "FLAG": (1, "u64", False),
    }
    assert constants == set()

    scaffold = render_stub_scaffold(unknown_types, functions, constants)
    assert "type OsMemPoolHead = u64;" in scaffold
    assert "unsafe fn MEM_LOCK(_a0: u64, _a1: u64) -> ()" in scaffold
    assert "unsafe fn OsMemAlloc(_a0: u64, _a1: u64, _a2: u64) -> u64" in scaffold
    assert "unsafe fn FLAG(_a0: u64) -> u64" in scaffold


def test_stub_scaffold_collects_constants():
    effect = Sequence([Assign("acc", BinOp("+", Var("acc"), Var("OS_MEM_MIN_ALLOC_SIZE")))])
    unknown_types, functions, constants, _fn_ptrs = collect_external_symbols(effect, [], [("acc", "Nat")], "Nat")
    assert constants == {"OS_MEM_MIN_ALLOC_SIZE"}
    assert "const OS_MEM_MIN_ALLOC_SIZE: u64 = 0;" in render_stub_scaffold(unknown_types, functions, constants)
