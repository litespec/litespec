"""Seam-level equivalence checks — the checks are now real."""

from litespec.equivalence.dispatch import dispatch
from litespec.equivalence.verifier import verify_function
from litespec.extraction import extract_function
from litespec.interscope.isir import emit_isir_module

_C = "unsigned int f(unsigned int n) { return n + 1; }"


def test_c_to_lir_seam_checks_lir():
    fn = extract_function(_C, "f")
    assert dispatch("c_to_lir", c_source=_C.encode(), lir=fn).status == "pass"
    assert dispatch("c_to_lir", c_source=_C.encode(), lir=None).status == "fail"


def test_lir_to_unsafe_seam_compiles():
    assert dispatch("lir_to_unsafe", lir=None, rust="pub fn f() {}").status == "pass"
    assert dispatch("lir_to_unsafe", lir=None, rust="fn f( {").status == "fail"
    assert dispatch("lir_to_unsafe", lir=None, rust=None).status == "warn"


def test_lir_to_isir_seam_validates():
    fn = extract_function(_C, "f")
    isir = emit_isir_module("f", fn.state_vars, fn.effect)
    assert dispatch("lir_to_isir", lir=fn, isir=isir).status == "pass"
    assert dispatch("lir_to_isir", lir=fn, isir={"isir_version": "0.1"}).status == "fail"


def test_verify_function_end_to_end_passes():
    result, chain = verify_function(_C, "f")
    assert result.status == "pass", (result.errors, result.warnings)
    assert len(chain.links) == 5


def test_verify_function_unknown_name_raises():
    import pytest

    with pytest.raises(ValueError):
        verify_function(_C, "does_not_exist")


def test_is_interpretable_accepts_memory_write_target():
    from litespec.equivalence.lir_interp import is_interpretable
    from litespec.lir.effect_expr_ast import Assign, Field, Index, IntLit, Var

    # a field/subscript write is interpretable via the flat memory model
    assert is_interpretable(Assign(Field(Var("head"), "freeListBitmap"), IntLit(1)))
    assert is_interpretable(Assign(Index(Var("head"), IntLit(0)), IntLit(1)))
    assert is_interpretable(Assign(Var("x"), IntLit(1)))  # plain local is fine


def test_c_to_lir_concretely_evaluates_pure_function():
    from litespec.equivalence.dispatch import dispatch
    from litespec.extraction import extract_function

    fn = extract_function("unsigned int f(unsigned int n) { return n + 1; }", "f")
    r = dispatch("c_to_lir", c_source=b"unsigned int f(unsigned int n){return n+1;}", lir=fn)
    assert r.status == "pass"
    assert any("concretely evaluated" in rep for rep in r.reports)


def test_concrete_evaluation_matches_expected_results():
    from litespec.equivalence.lir_interp import concrete_inputs, run_effect
    from litespec.extraction import extract_function

    fn = extract_function("unsigned int f(unsigned int n) { return n + 1; }", "f")
    inputs = concrete_inputs([("n", "Nat")])
    outs = {run_effect(fn.effect, env) for env in inputs}
    assert outs == {v + 1 for v in [0, 1, 2, 7, 64, 128]}


def test_interpreter_c_wrapping_mode():
    from litespec.equivalence.lir_interp import run_effect
    from litespec.extraction import extract_function

    fn = extract_function("unsigned int f(unsigned int n) { return n - 8; }", "f")
    assert run_effect(fn.effect, {"n": 0}) == -8  # unbounded (Python int)
    assert run_effect(fn.effect, {"n": 0}, bits=32) == 4294967288  # C UINT32 wraps


def test_differential_check_matches_compiled_c():
    import shutil

    import pytest

    if shutil.which("clang") is None:
        pytest.skip("clang not available")
    from litespec.equivalence.differential import differential_check
    from litespec.extraction import extract_function

    src = "UINT32 f(UINT32 n) { return (n << 3) - 8; }"
    lir = extract_function(src, "f")
    status, mismatches = differential_check(src, lir)
    assert status == "ok", mismatches


def test_config_selects_preproc_branches():
    from litespec.extraction import extract_function
    from litespec.extraction.config import Config

    src = b"int f(int x) {\n#ifdef FEATURE_A\n return x + 1;\n#else\n return x - 1;\n#endif\n}\n"
    on = extract_function(src, "f", config=Config(defined={"FEATURE_A"}))
    off = extract_function(src, "f", config=Config())
    assert "+" in repr(on.effect)
    assert "-" in repr(off.effect)
    assert repr(on.effect) != repr(off.effect)


def test_local_vars_collected_inside_preproc_block():
    from litespec.extraction import extract_function
    from litespec.extraction.config import Config

    src = b"int f(int x) {\n#if FLAG\n int y = x + 1;\n return y;\n#endif\n return x;\n}\n"
    fn = extract_function(src, "f", config=Config(values={"FLAG": 1}))
    assert ("y", "int") in fn.state_vars or any(n == "y" for n, _ in fn.state_vars)


def test_config_ifndef_and_else_branches():
    from litespec.extraction import extract_function
    from litespec.extraction.config import Config

    src = b"int f(int x) {\n#ifndef FLAG\n return x + 1;\n#else\n return x - 1;\n#endif\n}\n"
    off = extract_function(src, "f", config=Config())
    assert "+" in repr(off.effect) and "-" not in repr(off.effect)
    on = extract_function(src, "f", config=Config(defined={"FLAG"}))
    assert "-" in repr(on.effect) and "+" not in repr(on.effect)


def test_eval_pp_condition():
    from litespec.extraction.config import Config, eval_pp_condition

    cfg = Config(defined={"A"}, values={"B": 2})
    assert eval_pp_condition("defined(A)", cfg) is True
    assert eval_pp_condition("defined(C)", cfg) is False
    assert eval_pp_condition("B", cfg) is True  # value 2 → nonzero
    assert eval_pp_condition("UNDEF", cfg) is False  # undefined identifier → 0
    assert eval_pp_condition("0", cfg) is False
    assert eval_pp_condition("1", cfg) is True


def test_target_expr_deref_write():
    from litespec.extraction import extract_function
    from litespec.lir.effect_expr_ast import Assign, Index

    src = b"void f(unsigned int *p, unsigned int v) { *((unsigned int *)((unsigned long)p - 8)) = v; }\n"
    fn = extract_function(src, "f")
    assert isinstance(fn.effect, Assign)
    assert isinstance(fn.effect.target, Index)  # *addr = v ⇔ addr[0] = v


def test_unsigned_bits():
    from litespec.equivalence.differential import unsigned_bits

    assert unsigned_bits("UINT8") == 8
    assert unsigned_bits("UINT16") == 16
    assert unsigned_bits("UINT32") == 32
    assert unsigned_bits("UINT64") == 64
    assert unsigned_bits("VOID *") is None


def test_interpreter_shift_masking_matches_c():
    from litespec.equivalence.lir_interp import run_effect
    from litespec.extraction import extract_function

    fn = extract_function("unsigned int f(unsigned int n) { return n >> 64; }", "f")
    # C: n >> 64 is UB; clang masks the shift to n >> 0 → n
    assert run_effect(fn.effect, {"n": 5}, bits=32) == 5


def test_differential_check_detects_mismatch():
    import shutil

    import pytest

    if shutil.which("clang") is None:
        pytest.skip("clang not available")
    from litespec.equivalence.differential import differential_check
    from litespec.extraction import extract_function

    c_src = "UINT32 f(UINT32 n) { return n + 1; }"
    wrong_lir = extract_function("UINT32 f(UINT32 n) { return n + 2; }", "f")
    status, mismatches = differential_check(c_src, wrong_lir)
    assert status == "mismatch"
    assert mismatches


def test_bitwise_not_mapping():
    from litespec.extraction import extract_function
    from litespec.lir.effect_expr_ast import BinOp, IntLit, Var

    fn = extract_function("unsigned int f(unsigned int n) { return ~n; }", "f")
    # ~n → n ^ -1 (bitwise NOT, not dropped)
    assert fn.effect.expr == BinOp("^", IntLit(-1), Var("n"))
