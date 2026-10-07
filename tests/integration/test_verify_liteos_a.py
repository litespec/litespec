"""Formal verification of the ported LiteOS-A functions.

Runs the full layered equivalence chain (T_C ⊑ T_LIR ⊑ T_Unsafe ⊑ T_Safe ⊑_α T_ISIR)
with real artifacts per seam: LIR is non-trivial, Rust compiles, ISIR validates.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from litespec.equivalence import verify_function
from litespec.type_mapping import load_type_model

_SRC_PATH = Path("/tmp/los_memory_a.c")
SRC = _SRC_PATH.read_bytes() if _SRC_PATH.exists() else None

_FNS = [
    "OsMemFlGet",
    "OsMemSlGet",
    "OsMemFreeListIndexGet",
    "OsMemNotEmptyIndexGet",
    "OsMemFindCurSuitableBlock",
    "OsMemFindNextSuitableBlock",
    "LOS_MemAlloc",
    "LOS_MemFree",
    "LOS_MemAllocAlign",
    "LOS_MemPoolSizeGet",
    "LOS_MemTotalUsedGet",
    # functions that read/write file-scope globals (regression for globals modeling)
    "OsMemPoolAdd",
    "OsMemPoolDelete",
    "OsKHeapInit",
]


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A source not present at /tmp/los_memory_a.c")
@pytest.mark.parametrize("name", _FNS)
def test_liteos_a_function_is_verified(name):
    result, chain = verify_function(SRC, name, type_model=load_type_model("liteos"))
    assert result.status == "pass", f"{name}: errors={result.errors} warnings={result.warnings}"
    assert len(chain.links) == 5  # the five-seam refinement chain is recorded
