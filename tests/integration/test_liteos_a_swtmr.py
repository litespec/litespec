"""Integration tests for the ported LiteOS-A software timer (los_swtmr.c)."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.config import Config
from litespec.lowering import port_module
from litespec.type_mapping import load_type_model

SRC = Path("/tmp/los_swtmr_combined.c")
if not SRC.exists():
    SRC = None
SRC2 = Path("/tmp/los_swtmr2_combined.c")
if not SRC2.exists():
    SRC2 = None


def _fns(src: bytes) -> list[str]:
    seen: set[str] = set()
    out = []
    for f in functions(parse_c(src)):
        if f.name and f.name not in seen:
            seen.add(f.name)
            out.append(f.name)
    return out


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A swtmr source not present")
def test_swtmr_create():
    # LOS_SwtmrCreate: validation + free-list pop (container_of) + *swtmrID output param.
    src = SRC.read_bytes()
    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    rust += (
        "\nfn main() { unsafe {\n"
        "  __write(0+0, 0x2000); __write(0+1, 0x2000);\n"
        "  __write(0x2000+0, 0); __write(0x2000+1, 0); __write(0x2000+6, 42);\n"
        "  let slot: u32 = 0x3000;\n"
        "  let ret = LOS_SwtmrCreate(0x100, 0, 0x1234, slot, 0x999);\n"
        '  println!("ret={} id={}", ret, __read(slot));\n'
        '  println!("s={} m={} i={} e={} a={:#x} h={:#x} o={}", __read(0x2000+4), __read(0x2000+5), __read(0x2000+9), __read(0x2000+10), __read(0x2000+11), __read(0x2000+12), __read(0x2000+13));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "swtmr.rs"
        exe = Path(d) / "swtmr"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "ret=0"  # LOS_OK
        assert out[1] == "id=42"  # *swtmrID = usTimerID (output param)
        assert out[2] == "s=1"  # ucState = OS_SWTMR_STATUS_CREATED
        assert out[3] == "m=0"  # ucMode = LOS_SWTMR_MODE_ONCE
        assert out[4] == "i=256"  # uwInterval = 0x100
        assert out[5] == "e=256"  # uwExpiry = 0x100
        assert out[6] == "a=0x999"  # uwArg
        assert out[7] == "h=0x1234"  # pfnHandler
        assert out[8] == "o=0"  # uwOwnerPid = NULL


@pytest.mark.skipif(SRC2 is None, reason="real LiteOS-A swtmr source not present")
def test_swtmr_lifecycle():
    # LOS_SwtmrStart/Stop/Delete: modulo ID index + status switch dispatch + state transitions.
    src = SRC2.read_bytes()
    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    rust += (
        "\nfn main() { unsafe {\n"
        "  g_swtmrCBArray = 0x2000; let t: u32 = 0x2000 + 42*15;\n"
        '  __write(t+6, 42); __write(t+4, 1); println!("a={}", LOS_SwtmrStart(42));\n'
        '  __write(t+4, 0); println!("b={}", LOS_SwtmrStart(42));\n'
        '  __write(t+4, 2); println!("c={}", LOS_SwtmrStart(42));\n'
        '  __write(t+4, 1); println!("d={}", LOS_SwtmrStop(42));\n'
        '  __write(t+4, 2); println!("e={} s={}", LOS_SwtmrStop(42), __read(t+4));\n'
        '  __write(t+4, 1); println!("f={} s={}", LOS_SwtmrDelete(42), __read(t+4));\n'
        '  println!("g={}", LOS_SwtmrStart(0xFFFF));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "swtmr2.rs"
        exe = Path(d) / "swtmr2"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "a=0"  # CREATED → SwtmrStart → LOS_OK
        assert out[1] == "b=33555206"  # UNUSED → LOS_ERRNO_SWTMR_NOT_CREATED
        assert out[2] == "c=0"  # TICKING → stop + start → LOS_OK
        assert out[3] == "d=33555213"  # CREATED → LOS_ERRNO_SWTMR_NOT_STARTED
        assert out[4] == "e=0"  # TICKING → SwtmrStop → LOS_OK
        assert out[5] == "s=1"  # state → CREATED after stop
        assert out[6] == "f=0"  # CREATED → SwtmrDelete → LOS_OK
        assert out[7] == "s=0"  # state → UNUSED after delete
        assert out[8] == "g=33555205"  # swtmrID >= MAX → LOS_ERRNO_SWTMR_ID_INVALID
