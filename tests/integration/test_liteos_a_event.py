"""Integration tests for the ported LiteOS-A event (los_event.c).

Verifies the pointer-dereference (`*ptr`) support that the event poll logic needs.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.config import Config
from litespec.extraction.size_table import compute_sizes
from litespec.extraction.struct_table import StructTable
from litespec.lowering import port_module
from litespec.type_mapping import load_type_model

SRC = Path("/tmp/los_event_combined.c")
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


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A event source not present")
def test_event_struct_layout():
    src = SRC.read_bytes()
    st = StructTable.from_translation_unit(parse_c(src))
    sizes = compute_sizes(st)
    assert sizes["EVENT_CB_S"] == 3
    off = st.field_offsets(sizes)
    assert off["uwEventID"] == 0
    assert off["stEventList"] == 1


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A event source not present")
def test_event_poll_and_lifecycle():
    src = SRC.read_bytes()
    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    rust += (
        "\nfn main() { unsafe {\n"
        "  let eventCB: u32 = 0x2000; let eventID: u32 = 0x2100;\n"
        '  println!("init={}", LOS_EventInit(eventCB));\n'
        '  println!("write={} uwEventID={:#x}", LOS_EventWrite(eventCB, 0x0F), __read(eventCB+0));\n'
        "  __write(eventID, 0x0F);\n"
        '  println!("pollOR={:#x}", LOS_EventPoll(eventID, 0x03, 2));\n'
        "  __write(eventID, 0x0F);\n"
        '  println!("pollAND={:#x}", LOS_EventPoll(eventID, 0x0F, 4));\n'
        "  __write(eventID, 0x05);\n"
        '  println!("pollAND2={:#x}", LOS_EventPoll(eventID, 0x0F, 4));\n'
        '  println!("clear={} uwEventID={:#x}", LOS_EventClear(eventCB, 0x0C), __read(eventCB+0));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "event.rs"
        exe = Path(d) / "event"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "init=0"
        assert out[1] == "write=0"
        assert out[2] == "uwEventID=0xf"  # 0x0F written
        assert out[3] == "pollOR=0x3"  # 0x0F & 0x03 (OR mode)
        assert out[4] == "pollAND=0xf"  # 0x0F == 0x0F & 0x0F (AND mode)
        assert out[5] == "pollAND2=0x0"  # 0x0F != 0x05 (AND mode → 0)
        assert out[6] == "clear=0"
        assert out[7] == "uwEventID=0xc"  # 0x0F & 0x0C
