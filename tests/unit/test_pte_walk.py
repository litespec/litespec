"""Page-table descriptor walk (32-bit ARMv6/v7): the extractor resolves the bit-field math.

Verifies the *core* of ``LOS_ArchMmuQuery`` — the L1/L2 descriptor field extraction
(``MMU_DESCRIPTOR_L1_SECTION_ADDR``, ``…_PAGE_TABLE_ADDR``, ``…_L2_SMALL_PAGE_ADDR``,
type discriminators) and the L1/L2 index computation — folds to the correct 32-bit
values under the word model. These are plain u32 shift/mask operations, so this is the
part of the page-table walk that must be target-width-correct.
"""

from __future__ import annotations

from pathlib import Path

from litespec.extraction import parse_c
from litespec.extraction.macro_resolution import _expr_from_text, _resolve_expr
from litespec.extraction.macro_table import MacroTable
from litespec.equivalence.lir_interp import run_effect
from litespec.extraction import extract_function

REPO = Path(__file__).resolve().parents[2]
LITEOS = REPO / "third_party" / "liteos"
DESCRIPTOR = LITEOS / "arch" / "arm" / "arm" / "include" / "los_mmu_descriptor_v6.h"
PTE_OPS = LITEOS / "arch" / "arm" / "arm" / "include" / "los_pte_ops.h"


def _resolve(expr_text: str) -> int:
    src = (DESCRIPTOR.read_text(encoding="utf-8") + "\n" + PTE_OPS.read_text(encoding="utf-8")).encode()
    mt = MacroTable.from_translation_unit(parse_c(src))
    e = _resolve_expr(_expr_from_text(expr_text), mt, 0)
    return e.value


def test_l1_section_addr_masks_low_20_bits():
    assert _resolve("MMU_DESCRIPTOR_L1_SECTION_ADDR(0x12345002)") == 0x12300000


def test_l1_page_table_addr_masks_low_10_bits():
    assert _resolve("MMU_DESCRIPTOR_L1_PAGE_TABLE_ADDR(0x80000402)") == 0x80000400


def test_l2_small_page_addr_masks_low_12_bits():
    assert _resolve("MMU_DESCRIPTOR_L2_SMALL_PAGE_ADDR(0x56789002)") == 0x56789000


def test_l1_type_discriminators():
    assert _resolve("MMU_DESCRIPTOR_L1_TYPE_MASK") == 0x3
    assert _resolve("MMU_DESCRIPTOR_L1_TYPE_SECTION") == 0x2
    assert _resolve("MMU_DESCRIPTOR_L1_TYPE_PAGE_TABLE") == 0x1
    assert _resolve("MMU_DESCRIPTOR_L1_TYPE_INVALID") == 0x0


def test_pte_index_computation():
    # OsGetPte1Index(va) = va >> 20 ; OsGetPte2Index(va) = (va & 0xFFFFF) >> 12
    assert _resolve("(0x400000 >> 20)") == 4
    assert _resolve("((0x400123 & 0xFFFFF) >> 12)") == 0
    assert _resolve("((0x456000 & 0xFFFFF) >> 12)") == 0x56  # 0x56000 >> 12


def test_pte_op_is_section_folds():
    src = (DESCRIPTOR.read_text(encoding="utf-8") + "\n" + PTE_OPS.read_text(encoding="utf-8")).encode()
    fn = extract_function(src, "OsIsPte1Section")
    assert run_effect(fn.effect, {"pte1": 0x2}, 32) == 1  # (0x2 & 0x3) == 0x2
    assert run_effect(fn.effect, {"pte1": 0x1}, 32) == 0  # page-table, not section
