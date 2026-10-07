"""Declarative table of C builtin/intrinsic names → semantic operations.

This is the single source of truth for how C intrinsic-like calls are interpreted.
Both the lowering (``render_expr_rust``) and the interpreter (``_eval_expr``)
consult ``lookup``, so an intrinsic is declared once instead of string-matched in
several places.

Extending the pipeline to a new target/board means adding entries here, or — for
target-specific MMIO macros — declaring them in the target config's ``mmio``
section and calling ``register_mmio_from_target``. No per-intrinsic code in the
lowering or interpreter.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Op(Enum):
    """Semantic operation an intrinsic performs (rendered/evaluated by consumers)."""

    LEADING_ZEROS = "leading_zeros"  # CLZ(x)
    TRAILING_ZEROS = "trailing_zeros"  # CTZ(x)
    FFSL = "ffsl"  # __builtin_ffsl(x) = x ? 1 + trailing_zeros(x) : 0
    ALIGN = "align"  # LOS_Align(addr, boundary) = (addr + boundary - 1) & ~(boundary - 1)
    CURR_TASK_GET = "curr_task_get"  # ArchCurrTaskGet() → the word-sized current-task cell
    CURR_TASK_SET = "curr_task_set"  # ArchCurrTaskSet(val) → write the current-task cell
    CURR_CPUID = "curr_cpuid"  # ArchCurrCpuid() → the word-sized current-CPU-id cell
    IDENTITY = "identity"  # f(x) = x (flat-model physical↔virtual translation)
    ATOMIC_LOAD = "atomic_load"  # LOS_AtomicRead(v)
    ATOMIC_STORE = "atomic_store"  # LOS_AtomicSet(v, val)
    ATOMIC_ADD = "atomic_add"  # LOS_AtomicAdd(v, d) — fetch-add, returns old
    ATOMIC_SUB = "atomic_sub"  # LOS_AtomicSub(v, d) — fetch-sub, returns old
    ATOMIC_INC = "atomic_inc"  # LOS_AtomicInc(v) — void increment
    ATOMIC_DEC = "atomic_dec"  # LOS_AtomicDec(v) — void decrement
    ATOMIC_DEC_RET = "atomic_dec_ret"  # LOS_AtomicDecRet(v) — returns new
    ATOMIC_CMPXCHG = "atomic_cmpxchg"  # LOS_AtomicCmpXchg32bits(v, val, old) — returns bool
    MEM_ALLOC = "mem_alloc"  # LOS_MemAlloc(pool, size) — bump-allocator (returns word addr)
    MEM_ALLOC_ALIGN = "mem_alloc_align"  # LOS_MemAllocAlign(pool, size, align)
    MMIO_READ = "mmio_read"  # volatile device read (separate from RAM)
    MMIO_WRITE = "mmio_write"  # volatile device write (separate from RAM)
    NOOP = "noop"  # logging/hook helper: discard args, yield 0


@dataclass(frozen=True)
class Intrinsic:
    """A C name and the operation it denotes, plus the argument-count contract.

    ``arity`` is the exact argument count, or ``None`` for variadic intrinsics.
    """

    op: Op
    arity: int | None


#: C name → intrinsic operation. ``arity`` guards the call shape before dispatch
#: (``None`` accepts any argument count). MMIO entries are target-specific and are
#: added by ``register_mmio`` (see ``config/targets/*.yaml`` → ``mmio``).
INTRINSICS: dict[str, Intrinsic] = {
    "CLZ": Intrinsic(Op.LEADING_ZEROS, 1),
    "CTZ": Intrinsic(Op.TRAILING_ZEROS, 1),
    # GCC / ARM-compiler builtin spellings (macros like CLZ lower to these).
    "__builtin_clz": Intrinsic(Op.LEADING_ZEROS, 1),
    "__builtin_clzl": Intrinsic(Op.LEADING_ZEROS, 1),
    "__builtin_clzll": Intrinsic(Op.LEADING_ZEROS, 1),
    "__builtin_ctz": Intrinsic(Op.TRAILING_ZEROS, 1),
    "__builtin_ctzl": Intrinsic(Op.TRAILING_ZEROS, 1),
    "__builtin_ctzll": Intrinsic(Op.TRAILING_ZEROS, 1),
    "__clz": Intrinsic(Op.LEADING_ZEROS, 1),
    "__ctz": Intrinsic(Op.TRAILING_ZEROS, 1),
    "__builtin_ffs": Intrinsic(Op.FFSL, 1),
    "__builtin_ffsl": Intrinsic(Op.FFSL, 1),
    "LOS_Align": Intrinsic(Op.ALIGN, 2),
    # CPU-register accessors: the current task is modeled as a word-sized cell,
    # not a CP15 register (TPIDRPRW) — target-independent across 32/64-bit.
    "ArchCurrTaskGet": Intrinsic(Op.CURR_TASK_GET, 0),
    "ArchCurrTaskSet": Intrinsic(Op.CURR_TASK_SET, 1),
    "ArchCurrCpuid": Intrinsic(Op.CURR_CPUID, 0),
    # flat-model physical↔virtual translation (identity in the word model)
    "LOS_PaddrToKVaddr": Intrinsic(Op.IDENTITY, 1),
    # atomics: read-modify-write on a memory word (single-threaded model).
    "LOS_AtomicRead": Intrinsic(Op.ATOMIC_LOAD, 1),
    "LOS_AtomicSet": Intrinsic(Op.ATOMIC_STORE, 2),
    "LOS_AtomicAdd": Intrinsic(Op.ATOMIC_ADD, 2),
    "LOS_AtomicSub": Intrinsic(Op.ATOMIC_SUB, 2),
    "LOS_AtomicInc": Intrinsic(Op.ATOMIC_INC, 1),
    "LOS_AtomicDec": Intrinsic(Op.ATOMIC_DEC, 1),
    "LOS_AtomicDecRet": Intrinsic(Op.ATOMIC_DEC_RET, 1),
    "LOS_AtomicCmpXchg32bits": Intrinsic(Op.ATOMIC_CMPXCHG, 3),
    # logging / hook no-ops (variadic)
    "PRINTK": Intrinsic(Op.NOOP, None),
    "PRINT_ERR": Intrinsic(Op.NOOP, None),
    "LOS_Panic": Intrinsic(Op.NOOP, None),
    "OsHookCall": Intrinsic(Op.NOOP, None),
}


def lookup(name: str) -> Intrinsic | None:
    """Return the intrinsic for a C call name, or ``None`` if it is not one."""
    return INTRINSICS.get(name)


def register_mmio(read_names, write_names) -> None:
    """Register target-specific MMIO read/write macro names into ``INTRINSICS``.

    Replaces any previously registered MMIO entries so switching targets does not
    accumulate stale macro names.
    """
    for name in [n for n, i in INTRINSICS.items() if i.op in (Op.MMIO_READ, Op.MMIO_WRITE)]:
        del INTRINSICS[name]
    for name in read_names:
        INTRINSICS[name] = Intrinsic(Op.MMIO_READ, 1)
    for name in write_names:
        INTRINSICS[name] = Intrinsic(Op.MMIO_WRITE, 2)


def register_mmio_from_target(target_name: str = "liteos") -> None:
    """Register the target's MMIO macro names (from its config's ``mmio`` section)."""
    from litespec.targets.loader import load_target

    t = load_target(target_name)
    register_mmio(t.mmio_read_macros, t.mmio_write_macros)


def c_macro(name: str, intr: Intrinsic) -> str | None:
    """C ``#define`` line for an intrinsic (reference-C preamble), or ``None``.

    ``None`` means the name needs no ``#define`` in C (e.g. ``__builtin_ffsl`` is a
    GCC builtin).
    """
    if intr.op is Op.LEADING_ZEROS:
        return f"#define {name}(x) __builtin_clz(x)"
    if intr.op is Op.TRAILING_ZEROS:
        return f"#define {name}(x) __builtin_ctz(x)"
    if intr.op is Op.MMIO_READ:
        return f"#define {name}(addr) (*(volatile unsigned int *)(addr))"
    if intr.op is Op.MMIO_WRITE:
        return f"#define {name}(addr, v) (*(volatile unsigned int *)(addr) = (v))"
    if intr.op is Op.NOOP:
        return f"#define {name}(...) ((void)0)"
    return None  # FFSL — GCC builtin
