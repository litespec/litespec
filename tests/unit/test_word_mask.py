"""Word-width masking in the LIR interpreter (the 32/64-bit abstraction).

Verifies the cell/atomic/pool/MMIO/CLZ helpers mask to the target's ``word_bits``
rather than a hardcoded 32 bits.
"""

import pytest

from litespec.equivalence import lir_interp as li
from litespec.intrinsics import Op


@pytest.fixture(autouse=True)
def _reset_word_bits():
    yield
    li.set_word_bits(32)


def test_32_bit_default():
    li.set_word_bits(32)
    assert li._mask(-1) == 0xFFFFFFFF
    assert li._mask(0x1_0000_0000) == 0  # truncates to 32-bit
    assert li._clz(1) == 31
    assert li._ctz(0x80000000) == 31
    assert li._ffsl(0x80000000) == 32


def test_64_bit_masking():
    li.set_word_bits(64)
    assert li._mask(-1) == 0xFFFFFFFFFFFFFFFF
    assert li._clz(1) == 63
    assert li._ctz(0x8000000000000000) == 63
    assert li._ffsl(0x8000000000000000) == 64


def test_64_bit_atomic_does_not_truncate():
    li.set_word_bits(64)
    mem: dict[int, int] = {}
    li._eval_intrinsic(Op.ATOMIC_STORE, [0x200, 0xFFFFFFFF + 1], mem)
    assert mem[0x200] == 0x100000000  # no 32-bit truncation
    li._eval_intrinsic(Op.ATOMIC_ADD, [0x200, 1], mem)
    assert mem[0x200] == 0x100000001


def test_64_bit_pool_bump_is_64_bit():
    li.set_word_bits(64)
    li._POOL_PTR = 0xFFFFFFFF - 5
    addr = li._eval_intrinsic(Op.MEM_ALLOC, [0, 10], {})
    assert addr == 0xFFFFFFFF - 5
    assert li._POOL_PTR == 0x100000004  # wrapped within 64-bit, no 32-bit clamp
