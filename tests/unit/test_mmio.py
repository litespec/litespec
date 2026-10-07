"""Unit tests for MMIO (memory-mapped I/O) support in the emitted Rust."""

import subprocess
import tempfile
from pathlib import Path

from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.config import Config
from litespec.lowering import port_module
from litespec.type_mapping import load_type_model

SRC = b"""
typedef unsigned int UINT32;
UINT32 mmio_roundtrip(UINT32 addr, UINT32 val) {
    WRITE_UINT32(addr, val);
    UINT32 r = READ_UINT32(addr);
    return r;
}
"""


def test_mmio_is_separate_from_ram():
    seen: set[str] = set()
    fns = []
    for f in functions(parse_c(SRC)):
        if f.name and f.name not in seen:
            seen.add(f.name)
            fns.append(f.name)
    rust = port_module(SRC, fns, type_model=load_type_model("liteos"), config=Config(), executable=True)
    assert "__read_mmio" in rust
    assert "__write_mmio" in rust
    assert "static mut MMIO" in rust  # host simulation: separate MMIO array (no arch gate)
    rust += (
        "\nfn main() { unsafe {\n"
        "  let r = mmio_roundtrip(0x9000, 0xDEADBEEF);\n"
        '  println!("r={:#x}", r);\n'
        '  println!("ram={:#x}", __read(0x9000));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "mmio.rs"
        exe = Path(d) / "mmio"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "r=0xdeadbeef"  # MMIO write then read round-trips
        assert out[1] == "ram=0x0"  # RAM at the same address is untouched
