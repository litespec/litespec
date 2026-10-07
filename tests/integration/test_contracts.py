"""Arch-neutral interface contract verification (the cross-arch EC seam).

Checks that the ``interface.contracts`` declared in a target config are loaded and
that each contract's observable check passes on that arch's combined source. The
``compare_contracts`` helper is what will later diff two archs (x86 vs arm, etc.).
"""

from pathlib import Path

import pytest

from litespec.equivalence.contracts import compare_contracts, verify_contracts
from litespec.targets.loader import load_target
from litespec.type_mapping import load_type_model

SRC = Path("/tmp/los_arch_mmu_combined.c")
SRC = SRC if SRC.exists() else None


@pytest.mark.skipif(SRC is None, reason="arch_mmu combined source not present")
def test_target_declares_contracts_and_memory_model():
    target = load_target("liteos")
    assert any(c["fn"] == "LOS_ArchMmuQuery" and c["spec"] == "mmu_query" for c in target.interface_contracts)
    # the descriptor model is arch-declared (config-driven), not hardcoded
    assert target.memory_config["l1_index_shift"] == 20
    assert target.memory_config["l1_section_type"] == 0x2
    assert target.memory_config["l1_section_frame"] == 0xFFF00000
    assert target.memory_config["l1_section_offset_mask"] == 0xFFFFF


@pytest.mark.skipif(SRC is None, reason="arch_mmu combined source not present")
def test_mmu_query_contract_passes():
    target = load_target("liteos")
    tm = load_type_model(target.type_model)
    results = verify_contracts(SRC.read_bytes(), target.interface_contracts, tm, target.memory_config)
    assert [r.contract for r in results] == ["mmu_query"]
    assert results[0].status == "pass", results[0].reports
    # both observables held: unmapped → NOT_FOUND, section-mapped → paddr
    assert any("unmapped" in r and "✓" in r for r in results[0].reports)
    assert any("paddr" in r and "✓" in r for r in results[0].reports)


@pytest.mark.skipif(SRC is None, reason="arch_mmu combined source not present")
def test_mmu_query_contract_detects_wrong_descriptor_model():
    # If the declared descriptor model disagrees with the source's macros, the
    # contract must fail (this is exactly the cross-arch conformance check).
    target = load_target("liteos")
    tm = load_type_model(target.type_model)
    wrong = dict(target.memory_config)
    wrong["l1_section_frame"] = 0xFF000000  # 16MB sections, not ARMv6's 1MB
    results = verify_contracts(SRC.read_bytes(), target.interface_contracts, tm, wrong)
    assert results[0].status == "fail"


@pytest.mark.skipif(SRC is None, reason="arch_mmu combined source not present")
def test_compare_contracts_agrees_on_identical_source():
    target = load_target("liteos")
    tm = load_type_model(target.type_model)
    src = SRC.read_bytes()
    res = compare_contracts(src, src, target.interface_contracts, tm, tm, target.memory_config, target.memory_config)
    assert res["agree"] == ["mmu_query"]
    assert res["disagree"] == []
