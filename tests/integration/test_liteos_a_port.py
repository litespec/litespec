"""Deep tests for the LiteOS-A memory-module port.

Verifies *semantic* correctness (not just compilation): differential testing of
pure arithmetic paths against C semantics, and structural checks.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from litespec.extraction import extract_function, parse_c
from litespec.extraction.macro_resolution import _expr_from_text, _resolve_expr
from litespec.extraction.macro_table import MacroTable
from litespec.lir.effect_expr_ast import (
    Assign,
    BinOp,
    BoolLit,
    Compare,
    Conditional,
    IntLit,
    Not,
    Return,
    Sequence,
    Skip,
    Ternary,
    Var,
)
from litespec.lowering import port_module
from litespec.type_mapping import load_type_model

_SRC_PATH = Path("/tmp/los_memory_a.c")
SRC = _SRC_PATH.read_bytes() if _SRC_PATH.exists() else None

_ALL_FNS = [
    "OsMemFlGet",
    "OsMemSlGet",
    "OsMemFreeListIndexGet",
    "OsMemNotEmptyIndexGet",
    "OsMemFindCurSuitableBlock",
    "OsMemFindNextSuitableBlock",
    "OsMemSetFreeListBit",
    "OsMemClearFreeListBit",
    "OsMemListAdd",
    "OsMemListDelete",
    "OsMemFreeNodeAdd",
    "OsMemFreeNodeDelete",
    "OsMemFreeNodeGet",
    "OsMemMergeNode",
    "OsMemSplitNode",
    "OsMemCreateUsedNode",
    "OsMemAlloc",
    "LOS_MemAlloc",
    "LOS_MemAllocAlign",
    "LOS_MemFree",
    "LOS_MemPoolSizeGet",
    "LOS_MemTotalUsedGet",
]


# --- pure LIR interpreter (with return short-circuit) -----------------------


class _Return(Exception):
    def __init__(self, value):
        self.value = value


def eval_expr(e, env):
    if isinstance(e, IntLit):
        return e.value
    if isinstance(e, BoolLit):
        return e.value
    if isinstance(e, Var):
        return env[e.name]
    if isinstance(e, BinOp):
        l, r = eval_expr(e.left, env), eval_expr(e.right, env)
        return {
            "+": lambda: l + r,
            "-": lambda: l - r,
            "*": lambda: l * r,
            "/": lambda: l // r,
            "%": lambda: l % r,
            "<<": lambda: l << r,
            ">>": lambda: l >> r,
            "&": lambda: l & r,
            "|": lambda: l | r,
            "^": lambda: l ^ r,
            "and": lambda: bool(l) and bool(r),
            "or": lambda: bool(l) or bool(r),
        }[e.op]()
    if isinstance(e, Compare):
        l, r = eval_expr(e.left, env), eval_expr(e.right, env)
        return {"<": l < r, "<=": l <= r, ">": l > r, ">=": l >= r, "=": l == r, "!=": l != r}[e.op]
    if isinstance(e, Not):
        return not eval_expr(e.operand, env)
    if isinstance(e, Ternary):
        return eval_expr(e.then, env) if eval_expr(e.cond, env) else eval_expr(e.else_, env)
    raise ValueError(f"cannot eval {type(e).__name__}")


def _step(effect, env):
    if isinstance(effect, Return):
        raise _Return(eval_expr(effect.expr, env) if effect.expr is not None else None)
    if isinstance(effect, Conditional):
        _step(effect.then if eval_expr(effect.cond, env) else effect.else_, env)
    elif isinstance(effect, Sequence):
        for item in effect.items:
            _step(item, env)
    elif isinstance(effect, Assign):
        env[effect.target] = eval_expr(effect.expr, env)
    elif isinstance(effect, Skip):
        pass
    else:
        raise ValueError(f"cannot eval effect {type(effect).__name__}")


def run_effect(effect, env):
    """Evaluate an effect; returns the value of the first ``return`` reached, else None."""
    try:
        _step(effect, env)
        return None
    except _Return as r:
        return r.value


def _const_value(name):
    macros = MacroTable.from_translation_unit(parse_c(SRC))
    expr = _resolve_expr(_expr_from_text(macros.constants[name]), macros, 0)
    return eval_expr(expr, {})


# --- tests -------------------------------------------------------------------


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A source not present at /tmp/los_memory_a.c")
def test_full_memory_module_compiles():
    rust = port_module(SRC, _ALL_FNS, type_model=load_type_model("liteos"))
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        src = Path(d) / "out.rs"
        rlib = Path(d) / "lib.rlib"
        src.write_text(rust, encoding="utf-8")
        proc = subprocess.run(
            ["rustc", "--edition", "2021", "--crate-type", "lib", str(src), "-o", str(rlib)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert rlib.exists()


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A source not present")
def test_executable_module_runs_allocator_lifecycle():
    from litespec.extraction.c_translation_unit import functions
    from litespec.extraction.config import Config

    seen: set[str] = set()
    fns = []
    for f in functions(parse_c(SRC)):
        if f.name and f.name not in seen:
            seen.add(f.name)
            fns.append(f.name)
    rust = port_module(SRC, fns, type_model=load_type_model("liteos"), config=Config.liteos_default(), executable=True)
    rust += (
        "\nfn main() { unsafe {\n"
        "  let pool: u32 = 0x1000; let size: u32 = 0x1000;\n"
        "  let i0 = LOS_MemInit(pool, size);\n"
        "  let p1 = LOS_MemAlloc(pool, 32);\n"
        "  let p2 = LOS_MemAlloc(pool, 64);\n"
        "  let p3 = LOS_MemAllocAlign(pool, 100, 64);\n"
        "  let used = LOS_MemTotalUsedGet(pool);\n"
        "  let f1 = LOS_MemFree(pool, p1);\n"
        "  let used2 = LOS_MemTotalUsedGet(pool);\n"
        "  let ck = LOS_MemIntegrityCheck(pool);\n"
        '  println!("init={} p1={} p2={} p3={} used={} free={} used2={} integrity={}", i0, p1, p2, p3, used, f1, used2, ck);\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        src = Path(d) / "exe.rs"
        exe = Path(d) / "exe"
        src.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(src), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr  # runs the lifecycle without panicking
        out = dict(kv.split("=") for kv in run.stdout.split())
        assert out["init"] == "0"  # LOS_OK
        assert out["free"] == "0"  # LOS_OK
        assert out["integrity"] == "0"  # no corruption after alloc/free
        p1, p2, p3 = int(out["p1"]), int(out["p2"]), int(out["p3"])
        assert p1 != 0 and p2 != 0 and p3 != 0  # distinct, non-NULL allocations
        assert len({p1, p2, p3}) == 3
        assert p3 % 64 == 0  # allocAlign honours the 64-word boundary


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A source not present")
def test_os_mem_fl_get_pure_path_is_correct():
    # OsMemFlGet(size): if size < 128 return (size >> 2) - 1; else return OsMemLog2(size).
    fn = extract_function(SRC, "OsMemFlGet", type_model=load_type_model("liteos"))
    for size in [4, 8, 16, 64, 100, 124]:
        assert run_effect(fn.effect, {"size": size}) == (size >> 2) - 1


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A source not present")
def test_os_mem_free_list_index_get_pure_path():
    # OsMemFreeListIndexGet(size): for size < 128 returns fl = (size >> 2) - 1.
    # Its first branch returns fl after calling OsMemFlGet; the small-bucket path is pure.
    fn = extract_function(SRC, "OsMemFreeListIndexGet", type_model=load_type_model("liteos"))
    # The function's first statement is `fl = OsMemFlGet(size)` (a Call), so evaluate the
    # structural claim instead: the guard uses the expanded constant 128.
    guard = fn.effect.items[1].cond
    assert guard == Compare("<", Var("size"), IntLit(128))


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A source not present")
def test_macro_constants_evaluate_to_correct_values():
    assert _const_value("OS_MEM_SMALL_BUCKET_MAX_SIZE") == 128
    assert _const_value("OS_MEM_SMALL_BUCKET_COUNT") == 31
    assert _const_value("OS_MEM_LARGE_BUCKET_COUNT") == 24
    assert _const_value("OS_MEM_SLI") == 3
    assert _const_value("OS_MEM_FREE_LIST_COUNT") == 31 + (24 << 3)  # 223
    assert _const_value("OS_MEM_BITMAP_MASK") == 0x1F
    assert _const_value("OS_MEM_NODE_USED_FLAG") == 0x80000000


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A source not present")
def test_goto_becomes_labeled_block():
    from litespec.lir.effect_expr_ast import LabeledBlock
    from litespec.lowering.goto_elimination import eliminate_gotos

    fn = extract_function(SRC, "OsMemFindNextSuitableBlock", type_model=load_type_model("liteos"))
    out = eliminate_gotos(fn.effect)

    def has_labeled(effect):
        if isinstance(effect, LabeledBlock):
            return True
        if isinstance(effect, Sequence):
            return any(has_labeled(i) for i in effect.items)
        if isinstance(effect, Conditional):
            return has_labeled(effect.then) or has_labeled(effect.else_)
        return False

    assert has_labeled(out)


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A source not present")
def test_null_lowering():
    fn = extract_function(SRC, "LOS_MemAlloc", type_model=load_type_model("liteos"))
    cond = fn.effect.items[0]
    assert isinstance(cond, Conditional)
    # (pool == NULL) || (size == 0) → (pool == 0) || (size == 0)
    assert cond.cond == BinOp("or", Compare("=", Var("pool"), IntLit(0)), Compare("=", Var("size"), IntLit(0)))


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A source not present")
def test_field_access_lowering():
    from litespec.lir.effect_expr_ast import Field, Index

    fn = extract_function(SRC, "OsMemNotEmptyIndexGet", type_model=load_type_model("liteos"))

    def has_field_or_index(effect):
        if isinstance(effect, (Field, Index)):
            return True
        if isinstance(effect, Sequence):
            return any(has_field_or_index(i) for i in effect.items)
        if isinstance(effect, Conditional):
            return has_field_or_index(effect.then) or has_field_or_index(effect.else_)
        if isinstance(effect, Assign):
            return isinstance(effect.expr, (Field, Index))
        return False

    assert has_field_or_index(fn.effect)
