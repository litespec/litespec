"""Integration tests for the ported LiteOS-A message queue (los_queue.c).

Verifies the array-index scaling and array-element offsetof that the queue needs.
"""

from pathlib import Path

import pytest

from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.config import Config
from litespec.extraction.size_table import compute_sizes
from litespec.extraction.struct_table import StructTable
from litespec.lowering import port_module
from litespec.type_mapping import load_type_model

SRC = Path("/tmp/los_queue_combined.c")
if not SRC.exists():
    SRC = None


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A queue source not present")
def test_queue_struct_layout_and_array_element():
    src = SRC.read_bytes()
    st = StructTable.from_translation_unit(parse_c(src))
    sizes = compute_sizes(st)
    assert sizes["LosQueueCB"] == 15
    off = st.field_offsets(sizes)
    assert off["queueHandle"] == 0
    assert off["queueID"] == 4
    assert off["readWriteableCnt"] == 7
    assert off["readWriteList"] == 9
    assert off["memList"] == 13
    # array element size: readWriteList is an array of LOS_DL_LIST (2 words)
    assert st.field_elem_sizes(sizes)["readWriteList"] == 2


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A queue source not present")
def test_offsetof_array_element():
    # offsetof(LosQueueCB, readWriteList[1]) = 9 + 1*2 = 11
    from litespec.extraction.expression_mapping import set_field_elem_sizes, set_field_offsets, set_sizes
    from litespec.extraction.macro_resolution import _expr_from_text, _resolve_expr
    from litespec.extraction.macro_table import MacroTable

    src = SRC.read_bytes()
    st = StructTable.from_translation_unit(parse_c(src))
    sizes = compute_sizes(st)
    set_sizes(sizes)
    set_field_offsets(st.field_offsets(sizes))
    set_field_elem_sizes(st.field_elem_sizes(sizes))
    mt = MacroTable.from_translation_unit(parse_c(src))
    e = _resolve_expr(_expr_from_text("LOS_OFF_SET_OF(LosQueueCB, readWriteList[1])"), mt, 0)
    assert e.value == 11


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A queue source not present")
def test_queue_array_index_is_scaled():
    # the generated Rust must scale `readWriteList[i]` by the 2-word element size

    src = SRC.read_bytes()
    seen: set[str] = set()
    fns = []
    for f in functions(parse_c(src)):
        if f.name and f.name not in seen:
            seen.add(f.name)
            fns.append(f.name)
    rust = port_module(src, fns, type_model=load_type_model("liteos"), config=Config(), executable=True)
    assert "(1) * 2" in rust  # readWriteList[OS_QUEUE_WRITE] scales by 2 words
    assert "(0) * 2" in rust
