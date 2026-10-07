"""Integration tests for the ported LiteOS-A semaphore (los_sem.c).

Verifies the three things the semaphore exercises that earlier modules did not:
anonymous-struct typedefs, container_of/offsetof, and the count (post/pend) logic.
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

SRC = Path("/tmp/los_sem_combined.c")
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


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A sem source not present")
def test_anonymous_struct_typedef_is_captured():
    from litespec.extraction.struct_table import StructTable

    st = StructTable.from_translation_unit(parse_c(SRC.read_bytes()))
    assert "LosSemCB" in st.structs  # typedef struct { … } LosSemCB;
    off = st.field_offsets()
    assert off["semStat"] == 0
    assert off["semCount"] == 1
    assert off["maxSemCount"] == 2
    assert off["semID"] == 3
    assert off["semList"] == 4


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A sem source not present")
def test_offsetof_container_of():
    # GET_SEM_LIST(ptr) = LOS_DL_LIST_ENTRY(ptr, LosSemCB, semList) = ptr - offsetof(semList)
    from litespec.extraction import extract_function

    fn = extract_function(SRC.read_bytes(), "OsSemCreate", type_model=load_type_model("liteos"))
    text = str(fn.effect)
    # the container_of resolves to `unusedSem - 4` (semList is 4 words in)
    assert "4" in text  # the offset constant appears


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A sem source not present")
def test_semaphore_count_logic():
    src = SRC.read_bytes()
    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    rust += (
        "\nfn main() { unsafe {\n"
        "  g_allSem = 0x2000;\n"
        "  __write(0x2000, 1); __write(0x2001, 2); __write(0x2002, 5);\n"
        "  __write(0x2003, 0); __write(0x2004, 0x2004); __write(0x2005, 0x2004);\n"
        '  println!("post={} pend={} pend2={}", LOS_SemPost(0), LOS_SemPend(0, 0), LOS_SemPend(0, 0));\n'
        '  println!("count={}", __read(0x2001));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "sem.rs"
        exe = Path(d) / "sem"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        # post succeeds (LOS_OK=0), then pend twice; count ends at 2+1-1-1 = 1
        assert out[0] == "post=0"
        assert out[1] == "pend=0"
        assert out[2] == "pend2=0"
        assert out[3] == "count=1"
