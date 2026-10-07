"""emitted Rust compiles under rustc --edition 2021."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from litespec.extraction import extract_function
from litespec.lowering import emit_module

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


@pytest.mark.skipif(shutil.which("rustc") is None, reason="rustc not available")
def test_emitted_rust_compiles():
    fn = extract_function(_C, "sum_to")
    rust = emit_module("sum_to", [("n", "Nat")], "Nat", fn.state_vars, fn.effect)

    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        src = Path(d) / "out.rs"
        rlib = Path(d) / "libout.rlib"
        src.write_text(rust, encoding="utf-8")
        proc = subprocess.run(
            ["rustc", "--edition", "2021", "--crate-type", "lib", str(src), "-o", str(rlib)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert rlib.exists()


# A LiteOS-style function: pointer params, NULL checks, param reassignment,
# a struct-typed local, macro/helper calls, and a do{}while(0) with break.
_C_REAL = """\
VOID *LOS_MemAlloc(VOID *pool, UINT32 size) {
    if ((pool == NULL) || (size == 0)) { return NULL; }
    if (size < OS_MEM_MIN_ALLOC_SIZE) { size = OS_MEM_MIN_ALLOC_SIZE; }
    UINT32 intSave = 0;
    struct OsMemPoolHead *poolHead = (struct OsMemPoolHead *)pool;
    VOID *ptr = NULL;
    MEM_LOCK(poolHead, intSave);
    do {
        if (OS_MEM_NODE_GET_USED_FLAG(size)) { break; }
        ptr = OsMemAlloc(poolHead, size, intSave);
    } while (0);
    MEM_UNLOCK(poolHead, intSave);
    return ptr;
}
"""


@pytest.mark.skipif(shutil.which("rustc") is None, reason="rustc not available")
def test_real_los_memalloc_rust_compiles():
    from litespec.extraction.type_modeling import c_param_to_type_expr, c_return_to_type_expr
    from litespec.type_mapping import load_type_model

    tm = load_type_model("liteos")
    fn = extract_function(_C_REAL, "LOS_MemAlloc", type_model=tm)
    params = [(n, c_param_to_type_expr(t, n, type_model=tm)) for n, t in fn.parameters]
    ret = c_return_to_type_expr(fn.return_type, type_model=tm)
    rust = emit_module("LOS_MemAlloc", params, ret, fn.state_vars, fn.effect)

    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        src = Path(d) / "out.rs"
        rlib = Path(d) / "libout.rlib"
        src.write_text(rust, encoding="utf-8")
        proc = subprocess.run(
            ["rustc", "--edition", "2021", "--crate-type", "lib", str(src), "-o", str(rlib)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert rlib.exists()


# A linked-list walk: field access + subscript + a for loop with pointer step.
_C_LOOP = """\
struct Node { unsigned int size; struct Node *next; };
struct Node *find(struct Node *head, unsigned int size) {
    struct Node *node;
    for (node = head; node != 0; node = node->next) {
        if (node->size >= size) { return node; }
    }
    return 0;
}
"""


@pytest.mark.skipif(shutil.which("rustc") is None, reason="rustc not available")
def test_field_access_loop_rust_compiles():
    from litespec.extraction.type_modeling import c_param_to_type_expr, c_return_to_type_expr

    fn = extract_function(_C_LOOP, "find")
    params = [(n, c_param_to_type_expr(t, n)) for n, t in fn.parameters]
    ret = c_return_to_type_expr(fn.return_type)
    rust = emit_module("find", params, ret, fn.state_vars, fn.effect)

    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        src = Path(d) / "out.rs"
        rlib = Path(d) / "libout.rlib"
        src.write_text(rust, encoding="utf-8")
        proc = subprocess.run(
            ["rustc", "--edition", "2021", "--crate-type", "lib", str(src), "-o", str(rlib)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert rlib.exists()


# A forward goto + label (the do{}while(0) idiom), lowered to a labeled block.
_C_GOTO = """\
int f(int x) {
    if (x > 0) { goto DONE; }
    return 0;
DONE:
    return 1;
}
"""


@pytest.mark.skipif(shutil.which("rustc") is None, reason="rustc not available")
def test_goto_rust_compiles():
    from litespec.extraction.type_modeling import c_param_to_type_expr, c_return_to_type_expr

    fn = extract_function(_C_GOTO, "f")
    params = [(n, c_param_to_type_expr(t, n)) for n, t in fn.parameters]
    ret = c_return_to_type_expr(fn.return_type)
    rust = emit_module("f", params, ret, fn.state_vars, fn.effect)
    assert "break 'DONE;" in rust  # goto lowered to a labeled break

    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        src = Path(d) / "out.rs"
        rlib = Path(d) / "libout.rlib"
        src.write_text(rust, encoding="utf-8")
        proc = subprocess.run(
            ["rustc", "--edition", "2021", "--crate-type", "lib", str(src), "-o", str(rlib)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert rlib.exists()
