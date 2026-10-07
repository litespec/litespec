"""Integration tests for the ported LiteOS-A sys module (los_sys.c)."""

from pathlib import Path

import pytest

SRC = Path("/tmp/los_sys_combined.c")
if not SRC.exists():
    SRC = None


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A sys source not present")
def test_sys_time_conversions_are_differentially_verified():
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
    assert by_fn["LOS_MS2Tick"] == "differential"
    assert by_fn["LOS_Tick2MS"] == "differential"
    assert by_fn["OsNS2Tick"] == "differential"


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A sys source not present")
def test_sys_time_conversion_values():
    # LOSCFG_BASE_CORE_TICK_PER_SECOND=100, so ms→tick is /10, tick→ms is *10.
    from litespec.equivalence.differential import build_fn_table
    from litespec.equivalence.lir_interp import run_effect

    table = build_fn_table(SRC.read_bytes())
    ms2tick = table["LOS_MS2Tick"][1]
    assert run_effect(ms2tick, {"millisec": 100}) == 10
    assert run_effect(ms2tick, {"millisec": 0}) == 0
    assert run_effect(ms2tick, {"millisec": 0xFFFFFFFF}) == 0xFFFFFFFF  # max → max
    tick2ms = table["LOS_Tick2MS"][1]
    assert run_effect(tick2ms, {"tick": 10}) == 100
    assert run_effect(tick2ms, {"tick": 0}) == 0
