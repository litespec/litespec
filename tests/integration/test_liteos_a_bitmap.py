"""Integration tests for the ported LiteOS-A bitmap module (los_bitmap.c).

Uses the real source (fetched to /tmp/los_bitmap_combined.c) when present, and
checks the builtins (CTZ / __builtin_ffsl) that the ported module relies on.
"""

from pathlib import Path

import pytest

SRC = Path("/tmp/los_bitmap_combined.c")
if not SRC.exists():
    SRC = None


def test_ctz_and_ffsl_builtins():
    from litespec.equivalence.lir_interp import _eval_intrinsic
    from litespec.intrinsics import lookup

    assert _eval_intrinsic(lookup("CLZ").op, [0b1000]) == 28  # 32-bit leading zeros of 0b1000
    assert _eval_intrinsic(lookup("CTZ").op, [0b1000]) == 3  # trailing zeros
    assert _eval_intrinsic(lookup("CTZ").op, [0]) == 32
    assert _eval_intrinsic(lookup("__builtin_ffsl").op, [0b1000]) == 4  # 1-indexed lowest set bit
    assert _eval_intrinsic(lookup("__builtin_ffsl").op, [0]) == 0


def test_sizeof_times_8_is_bit_count():
    # ``sizeof(T) * 8`` (C idiom for "bits in T") folds to word_count × 32 in the
    # word model (1 word = 32 bits), not word_count × 8.
    from litespec.extraction import parse_c
    from litespec.extraction.expression_mapping import set_sizes
    from litespec.extraction.macro_resolution import _expr_from_text
    from litespec.extraction.size_table import compute_sizes
    from litespec.extraction.struct_table import StructTable

    src = b"typedef unsigned int UINTPTR;\nstruct Node { UINTPTR a; UINTPTR b; UINTPTR c; };\n"
    set_sizes(compute_sizes(StructTable.from_translation_unit(parse_c(src))))
    assert _expr_from_text("sizeof(UINTPTR) * 8").value == 32
    assert _expr_from_text("sizeof(struct Node) * 8").value == 96  # 3 words × 32 bits
    assert _expr_from_text("sizeof(UINTPTR)").value == 1  # word count unchanged


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A bitmap source not present")
def test_bitmap_pure_functions_are_differentially_verified():
    from litespec.equivalence.coverage import coverage_report
    from litespec.extraction import parse_c
    from litespec.extraction.c_translation_unit import functions
    from litespec.extraction.config import Config
    from litespec.type_mapping import load_type_model

    src = SRC.read_bytes()
    seen: set[str] = set()
    fns = []
    for f in functions(parse_c(src)):
        if f.name and f.name not in seen:
            seen.add(f.name)
            fns.append(f.name)
    _, by_fn = coverage_report(src, fns, type_model=load_type_model("liteos"), config=Config())
    # The pure bit-scan functions are compile-and-run checked against real C.
    assert by_fn["Ffz"] == "differential"
    assert by_fn["LOS_HighBitGet"] == "differential"
    assert by_fn["LOS_LowBitGet"] == "differential"


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A bitmap source not present")
def test_bitmap_high_low_bit_get_values():
    from litespec.equivalence.differential import build_fn_table
    from litespec.equivalence.lir_interp import run_effect

    src = SRC.read_bytes()
    table = build_fn_table(src, config=None)
    # LOS_HighBitGet(bitmap): highest set bit index (0-based) or 32 for 0.
    high = run_effect(table["LOS_HighBitGet"][1], {"bitmap": 0b1})
    assert high == 0
    high = run_effect(table["LOS_HighBitGet"][1], {"bitmap": 0x80000000})
    assert high == 31
    assert run_effect(table["LOS_HighBitGet"][1], {"bitmap": 0}) == 32
    # LOS_LowBitGet(bitmap): lowest set bit index (0-based) or 32 for 0.
    assert run_effect(table["LOS_LowBitGet"][1], {"bitmap": 0b1000}) == 3
    assert run_effect(table["LOS_LowBitGet"][1], {"bitmap": 0}) == 32
