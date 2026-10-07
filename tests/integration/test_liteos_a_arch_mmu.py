"""Integration tests for the ported LiteOS-A arch MMU page-table walk (los_arch_mmu.c).

Verifies ``LOS_ArchMmuQuery`` — the L1/L2 descriptor walk that maps a virtual address
to a physical address — against hand-built page tables in the flat word model.
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

SRC = Path("/tmp/los_arch_mmu_combined.c")
if not SRC.exists():
    SRC = None

# The walk plus its PTE-op / flag-converter callees (ported as real functions).
_WALK_CLOSURE = {
    "LOS_ArchMmuQuery",
    "OsGetPte1", "OsGetPte1Ptr", "OsGetPte1Index",
    "OsIsPte1Invalid", "OsIsPte1Section", "OsIsPte1PageTable",
    "OsGetPte2", "OsGetPte2Index", "OsGetPte2BasePtr",
    "OsIsPte2SmallPage", "OsIsPte2SmallPageXN", "OsIsPte2LargePage",
    "OsCvtSecAttsToFlags", "OsCvtPte2AttsToFlags",
    "OsCvtSecFlagsToAttrs", "OsCvtSecCacheFlagsToMMUFlags", "OsCvtSecAccessFlagsToMMUFlags",
}


def _fns(src: bytes) -> list[str]:
    seen: set[str] = set()
    out = []
    for f in functions(parse_c(src)):
        if f.name and f.name not in seen and f.name in _WALK_CLOSURE:
            seen.add(f.name)
            out.append(f.name)
    return out


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A arch MMU source not present")
def test_arch_mmu_query_section_and_page_table_walk():
    src = SRC.read_bytes()
    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    rust += (
        "\nfn main() { unsafe {\n"
        # LosArchMmu at 0x1000; virtTtb (offset 4 under SMP) → L1 page table at 0x2000.
        "  let am: u32 = 0x1000; __write(am+4, 0x2000);\n"
        # L1[4] = section entry: type=0x2, base=0x12300000.
        "  __write(0x2000+4, 0x12345002);\n"
        "  let st1 = LOS_ArchMmuQuery(am, 0x400123, 0x3000, 0);\n"
        '  println!("s1={} p1={:#x}", st1, __read(0x3000));\n'
        # L1[4] = page-table entry: type=0x1, L2 base=0x5000 (1KB-aligned).
        "  __write(0x2000+4, 0x5001);\n"
        # L2[0] = small-page entry: type=0x2, base=0x56700000.
        "  __write(0x5000+0, 0x56700002);\n"
        "  let st2 = LOS_ArchMmuQuery(am, 0x400123, 0x3000, 0);\n"
        '  println!("s2={} p2={:#x}", st2, __read(0x3000));\n'
        # L1[4] = invalid entry → NOT_FOUND (non-zero status).
        "  __write(0x2000+4, 0x0);\n"
        "  let st3 = LOS_ArchMmuQuery(am, 0x400123, 0x3000, 0);\n"
        '  println!("s3={}", st3);\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "mmu.rs"
        exe = Path(d) / "mmu"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "s1=0"  # section → LOS_OK
        assert out[1] == "p1=0x12300123"  # 0x12300000 + (0x400123 & 0xFFFFF)
        assert out[2] == "s2=0"  # page-table → LOS_OK
        assert out[3] == "p2=0x56700123"  # 0x56700000 + (0x400123 & 0xFFF)
        assert out[4].startswith("s3=") and out[4] != "s3=0"  # invalid → LOS_ERRNO_VM_NOT_FOUND
