"""Integration tests for the ported LiteOS-A mutex (los_mux.c).

Verifies the features the mutex exercises: Rust-keyword identifiers, forward
struct references (fixpoint sizes), and the switch statement.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.config import Config
from litespec.lowering import port_module
from litespec.type_mapping import load_type_model

SRC = Path("/tmp/los_mux_combined.c")
if not SRC.exists():
    SRC = None


def _fns(src: bytes) -> list[str]:
    seen: set[str] = set()
    out = []
    for f in functions(parse_c(src)):
        if f.name and f.name not in seen:
            seen.add(f.name)
            out.append(f.name)
    return out


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A mux source not present")
def test_mux_struct_layout_and_forward_reference():
    from litespec.extraction.size_table import compute_sizes
    from litespec.extraction.struct_table import StructTable

    st = StructTable.from_translation_unit(parse_c(SRC.read_bytes()))
    sizes = compute_sizes(st)
    assert sizes["LosMuxAttr"] == 4  # protocol, prioceiling, type, reserved
    assert sizes["LosMux"] == 11  # includes LOS_DL_LIST (defined later → fixpoint)
    off = st.field_offsets(sizes)
    assert off["protocol"] == 0
    assert off["type"] == 2
    assert off["attr"] == 1
    assert off["muxList"] == 7
    assert off["muxCount"] == 10


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A mux source not present")
def test_switch_statement_maps_to_conditional():
    # LOS_MuxAttrSetProtocol uses `switch (protocol)`; it must not be dropped.
    from litespec.extraction import extract_function

    fn = extract_function(SRC.read_bytes(), "LOS_MuxAttrSetProtocol", type_model=load_type_model("liteos"))
    assert "Conditional" in str(fn.effect) or "Compare" in str(fn.effect)


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A mux source not present")
def test_mux_attr_init_and_lifecycle():
    src = SRC.read_bytes()
    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    rust += (
        "\nfn main() { unsafe {\n"
        "  let attr: u32 = 0x2000; let mux: u32 = 0x3000;\n"
        '  println!("init={}", LOS_MuxAttrInit(attr));\n'
        '  println!("proto={} prio={} typ={}", __read(attr+0), __read(attr+1), __read(attr+2));\n'
        '  println!("setType={} type={}", LOS_MuxAttrSetType(attr, 2), __read(attr+2));\n'
        '  println!("setProto={} proto={}", LOS_MuxAttrSetProtocol(attr, 2), __read(attr+0));\n'
        '  println!("setProtoBad={}", LOS_MuxAttrSetProtocol(attr, 99));\n'
        '  println!("muxInit={} valid={}", LOS_MuxInit(mux, attr), LOS_MuxIsValid(mux));\n'
        '  println!("magic={:#x}", __read(mux+0));\n'
        '  println!("destroy={} magicAfter={:#x}", LOS_MuxDestroy(mux), __read(mux+0));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "mux.rs"
        exe = Path(d) / "mux"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "init=0"  # LOS_OK
        assert out[1] == "proto=1"  # LOS_MUX_PRIO_INHERIT
        assert out[2] == "prio=31"  # OS_TASK_PRIORITY_LOWEST
        assert out[3] == "typ=1"  # LOS_MUX_DEFAULT
        assert out[4] == "setType=0"  # LOS_OK
        assert out[5] == "type=2"  # LOS_MUX_ERRORCHECK
        assert out[6] == "setProto=0"  # LOS_OK
        assert out[7] == "proto=2"  # LOS_MUX_PRIO_PROTECT
        assert out[8] == "setProtoBad=22"  # LOS_EINVAL (switch default)
        assert out[9] == "muxInit=0"  # LOS_OK
        assert out[10] == "valid=1"  # TRUE
        assert out[11] == "magic=0xebcfdea0"  # OS_MUX_MAGIC (pinned kernel 1b5d3de)
        assert out[12] == "destroy=0"  # LOS_OK
        assert out[13] == "magicAfter=0x0"  # memset to 0
