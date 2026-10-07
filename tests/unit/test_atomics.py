"""Atomic read-modify-write intrinsics (single-threaded SMP model).

Verifies the ``LOS_Atomic*`` operations — which the extractor maps to LIR atomic
intrinsics instead of the inline ``ldrex``/``strex`` ARM asm — behave with the
correct fetch/exchange semantics over the flat memory model.
"""

from litespec.equivalence.lir_interp import _eval_intrinsic
from litespec.intrinsics import Op


def test_atomic_load_store():
    mem: dict[int, int] = {}
    _eval_intrinsic(Op.ATOMIC_STORE, [0x100, 42], mem)
    assert _eval_intrinsic(Op.ATOMIC_LOAD, [0x100], mem) == 42


def test_atomic_add_fetch_returns_old():
    mem: dict[int, int] = {0x100: 10}
    assert _eval_intrinsic(Op.ATOMIC_ADD, [0x100, 5], mem) == 10  # returns old
    assert mem[0x100] == 15


def test_atomic_sub_fetch_returns_old():
    mem: dict[int, int] = {0x100: 10}
    assert _eval_intrinsic(Op.ATOMIC_SUB, [0x100, 3], mem) == 10
    assert mem[0x100] == 7


def test_atomic_inc_dec():
    mem: dict[int, int] = {0x100: 0}
    _eval_intrinsic(Op.ATOMIC_INC, [0x100], mem)
    _eval_intrinsic(Op.ATOMIC_INC, [0x100], mem)
    assert mem[0x100] == 2
    _eval_intrinsic(Op.ATOMIC_DEC, [0x100], mem)
    assert mem[0x100] == 1


def test_atomic_dec_ret_returns_new():
    mem: dict[int, int] = {0x100: 3}
    assert _eval_intrinsic(Op.ATOMIC_DEC_RET, [0x100], mem) == 2
    assert mem[0x100] == 2


def test_atomic_cmpxchg_swaps_only_on_match():
    mem: dict[int, int] = {0x100: 7}
    assert _eval_intrinsic(Op.ATOMIC_CMPXCHG, [0x100, 9, 7], mem) == 1  # swapped
    assert mem[0x100] == 9
    assert _eval_intrinsic(Op.ATOMIC_CMPXCHG, [0x100, 42, 7], mem) == 0  # no match
    assert mem[0x100] == 9  # unchanged
