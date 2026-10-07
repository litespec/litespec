"""Integration tests for the ported LiteOS-A doubly-linked list (los_list.h)."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.config import Config
from litespec.lowering import port_module
from litespec.type_mapping import load_type_model

SRC = Path("/tmp/los_list_combined.c")
if not SRC.exists():
    SRC = None


def _list_functions(src: bytes) -> list[str]:
    seen: set[str] = set()
    fns = []
    for f in functions(parse_c(src)):
        if f.name and f.name not in seen:
            seen.add(f.name)
            fns.append(f.name)
    return fns


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A list source not present")
def test_list_functions_are_interpretable():
    from litespec.equivalence.coverage import coverage_report

    src = SRC.read_bytes()
    counts, per_fn = coverage_report(src, _list_functions(src), type_model=load_type_model("liteos"), config=Config())
    # The list ops take struct pointers, so they are concretely evaluated, not
    # differentially compared against C. None should be a mismatch.
    assert counts.get("mismatch", 0) == 0
    assert per_fn["LOS_ListInit"] in ("concrete", "differential")
    assert per_fn["LOS_ListEmpty"] in ("concrete", "differential")


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A list source not present")
def test_list_lifecycle():
    src = SRC.read_bytes()
    rust = port_module(
        src, _list_functions(src), type_model=load_type_model("liteos"), config=Config(), executable=True
    )
    rust += (
        "\nfn main() { unsafe {\n"
        "  let head: u32 = 0x1000; let n1: u32 = 0x1002; let n2: u32 = 0x1004; let n3: u32 = 0x1006; let empty: u32 = 0x1010;\n"
        "  LOS_ListInit(head); LOS_ListInit(empty);\n"
        "  LOS_ListAdd(head, n1);\n"
        "  LOS_ListAdd(head, n2);\n"
        "  LOS_ListTailInsert(head, n3);\n"
        '  println!("empty0={} empty1={}", LOS_ListEmpty(head), LOS_ListEmpty(empty));\n'
        "  let mut p = __read(head + 1); let mut order = String::new();\n"
        "  while p != head { order += &p.to_string(); order.push(','); p = __read(p + 1); }\n"
        '  println!("order={}", order);\n'
        "  LOS_ListDelete(n1);\n"
        '  println!("headNext={}", __read(head + 1));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "list.rs"
        exe = Path(d) / "list"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        # empty0=0 (head has nodes) empty1=1 (empty list)
        assert out[0] == "empty0=0"
        assert out[1] == "empty1=1"
        # head -> n2 (0x1004=4100) -> n1 (0x1002=4098) -> n3 (0x1006=4102) -> head
        assert out[2] == "order=4100,4098,4102,"
        # after deleting n1, head->next is still n2
        assert out[3] == "headNext=4100"
