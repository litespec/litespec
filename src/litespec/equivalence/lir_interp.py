"""Concrete LIR interpretation for differential checking (Phase 8).

Provides a small interpreter for the *pure* fragment of the LIR (arithmetic,
comparison, ternary, conditionals, sequences, assignment, return) plus purity
classification and concrete input generation. Used to add a semantic (concrete
evaluation) check on top of the structural seam checks.
"""

from __future__ import annotations

from itertools import product

from litespec.intrinsics import Op, lookup
from litespec.lir.effect_expr_ast import (
    AddrOf,
    Assign,
    BinOp,
    BoolLit,
    Call,
    Compare,
    Conditional,
    Deref,
    Field,
    Index,
    IntLit,
    Not,
    Return,
    Sequence,
    Skip,
    Ternary,
    Var,
)

MAX_INPUTS = 64

#: Interpretable builtins (compiler intrinsics), name → implementation.
_BUILTINS: dict[str, callable] = {}

#: Ported-function table (name → (param names, effect, return-width)), for inter-function interpretation.
_FN_TABLE: dict[str, tuple[tuple[str, ...], object, int | None]] = {}

#: Struct-field word offsets (name → offset), for the flat memory model.
_FIELD_OFFSETS: dict[str, int] = {}

#: Struct-scoped field offsets (``struct.field`` → offset), preferring no collisions.
_SCOPED_OFFSETS: dict[str, int] = {}

#: variable name → struct type name (from params/locals), for struct-scoped field offsets.
_VAR_STRUCT_TYPES: dict[str, str] = {}

#: ``struct.field`` → field base type name (for resolving nested ``a->b->c``).
_FIELD_TYPES: dict[str, str] = {}

#: Embedded sub-struct field names (Field access yields the sub-struct address).
_EMBEDDED: frozenset[str] = frozenset()

#: Separate MMIO device memory (address → word), so device access does not alias RAM.
_MMIO_MEM: dict[int, int] = {}

#: current-task cell (abstraction of the CPU's TPIDRPRW register).
_CURR_TASK: int = 0

#: current-CPU-id cell (abstraction of the MPIDR register).
_CURR_CPUID: int = 0

#: bump-allocator cursor (abstraction of the flat word model's memory pool).
_POOL_PTR: int = 0x3000

#: word-width mask (from the target's ``word_bits``; default 32-bit).
_MASK: int = 0xFFFFFFFF


def set_word_bits(bits: int) -> None:
    """Set the word width used for cell/atomic/pool/MMIO/CLZ masking."""
    global _MASK
    _MASK = (1 << bits) - 1


def _mask(v: int) -> int:
    return v & _MASK


def _mmio_read(addr: int) -> int:
    return _MMIO_MEM.get(_mask(addr), 0)


def _mmio_write(addr: int, v: int) -> int:
    _MMIO_MEM[_mask(addr)] = _mask(v)
    return 0


def _eval_intrinsic(op: Op, args: list[int], mem: dict | None = None) -> int:
    """Evaluate an intrinsic operation (canonicalized in litespec.intrinsics)."""
    global _CURR_TASK, _POOL_PTR
    if op is Op.LEADING_ZEROS:
        return _clz(args[0])
    if op is Op.TRAILING_ZEROS:
        return _ctz(args[0])
    if op is Op.FFSL:
        return _ffsl(args[0])
    if op is Op.ALIGN:
        return (args[0] + args[1] - 1) & ~(args[1] - 1)
    if op is Op.CURR_TASK_GET:
        return _CURR_TASK
    if op is Op.CURR_TASK_SET:
        _CURR_TASK = _mask(args[0])
        return 0
    if op is Op.CURR_CPUID:
        return _CURR_CPUID
    if op is Op.IDENTITY:
        return args[0]

    def _ld(addr: int) -> int:
        return mem.get(addr, 0) if mem is not None else 0

    def _st(addr: int, v: int) -> None:
        if mem is not None:
            mem[addr] = _mask(v)

    if op is Op.ATOMIC_LOAD:
        return _ld(args[0])
    if op is Op.ATOMIC_STORE:
        _st(args[0], args[1])
        return 0
    if op is Op.ATOMIC_ADD:
        old = _ld(args[0])
        _st(args[0], old + args[1])
        return old
    if op is Op.ATOMIC_SUB:
        old = _ld(args[0])
        _st(args[0], old - args[1])
        return old
    if op is Op.ATOMIC_INC:
        old = _ld(args[0])
        _st(args[0], old + 1)
        return old
    if op is Op.ATOMIC_DEC:
        old = _ld(args[0])
        _st(args[0], old - 1)
        return old
    if op is Op.ATOMIC_DEC_RET:
        new = _mask(_ld(args[0]) - 1)
        _st(args[0], new)
        return new
    if op is Op.ATOMIC_CMPXCHG:
        if _ld(args[0]) == args[2]:
            _st(args[0], args[1])
            return 1
        return 0
    if op is Op.MEM_ALLOC:
        addr = _POOL_PTR
        _POOL_PTR = _mask(addr + args[1])
        return addr
    if op is Op.MEM_ALLOC_ALIGN:
        align = args[2]
        addr = _mask((_POOL_PTR + align - 1) & ~(align - 1))
        _POOL_PTR = _mask(addr + args[1])
        return addr
    if op is Op.MMIO_READ:
        return _mmio_read(args[0])
    if op is Op.MMIO_WRITE:
        return _mmio_write(args[0], args[1])
    if op is Op.NOOP:
        return 0  # logging/hook helper: discard args
    return 0


def _clz(x: int) -> int:
    """Count leading zeros of the word (``__builtin_clz``)."""
    width = _MASK.bit_length()
    x &= _MASK
    return width - x.bit_length() if x else width


def _ctz(x: int) -> int:
    """Count trailing zeros of the word (``__builtin_ctz``)."""
    width = _MASK.bit_length()
    x &= _MASK
    return (x & -x).bit_length() - 1 if x else width


def _ffsl(x: int) -> int:
    """1-indexed position of the lowest set bit, 0 for 0 (``__builtin_ffsl``)."""
    x &= _MASK
    return (x & -x).bit_length() if x else 0


def set_identity_casts(names) -> None:
    """Register typedef names that are integer identity casts (``UINT32(x)`` → ``x``).

    Derived from the type model's ``c_to_lir`` (every non-``Unit`` mapping is a word-
    promoted or 64-bit integer, so the cast is the identity in the interpreter).
    """
    for t in names:
        _BUILTINS[t] = lambda x: x


def set_fn_table(table: dict) -> None:
    """Register ported functions so ``Call`` nodes can be interpreted across functions."""
    global _FN_TABLE
    _FN_TABLE = dict(table)


def set_field_offsets(offsets: dict[str, int]) -> None:
    """Register struct-field word offsets for the flat memory model."""
    global _FIELD_OFFSETS
    _FIELD_OFFSETS = dict(offsets)


def set_scoped_field_offsets(offsets: dict[str, int]) -> None:
    """Register struct-scoped (``struct.field`` → offset) field offsets."""
    global _SCOPED_OFFSETS
    _SCOPED_OFFSETS = dict(offsets)


def set_var_struct_types(types: dict[str, str]) -> None:
    """Register variable name → struct type name for scoped field offsets."""
    global _VAR_STRUCT_TYPES
    _VAR_STRUCT_TYPES = dict(types)


def set_field_types(types: dict[str, str]) -> None:
    """Register ``struct.field`` → field base type name for nested field resolution."""
    global _FIELD_TYPES
    _FIELD_TYPES = dict(types)


def set_embedded_fields(names) -> None:
    """Register embedded sub-struct field names (Field access yields the address)."""
    global _EMBEDDED
    _EMBEDDED = frozenset(names)


def is_pure_expr(expr) -> bool:
    if isinstance(expr, (IntLit, BoolLit, Var)):
        return True
    if isinstance(expr, (BinOp, Compare)):
        return is_pure_expr(expr.left) and is_pure_expr(expr.right)
    if isinstance(expr, Not):
        return is_pure_expr(expr.operand)
    if isinstance(expr, Ternary):
        return is_pure_expr(expr.cond) and is_pure_expr(expr.then) and is_pure_expr(expr.else_)
    if isinstance(expr, Call):
        known = expr.name in _FN_TABLE or expr.name in _BUILTINS or lookup(expr.name) is not None
        return known and all(is_pure_expr(a) for a in expr.args)
    if isinstance(expr, Field):
        return is_pure_expr(expr.base)
    if isinstance(expr, Index):
        return is_pure_expr(expr.base) and is_pure_expr(expr.index)
    return False


def is_interpretable(effect) -> bool:
    """True iff the effect uses only the evaluable fragment (arithmetic + memory; no loops/goto)."""
    if isinstance(effect, Return):
        return effect.expr is None or is_pure_expr(effect.expr)
    if isinstance(effect, Conditional):
        return is_pure_expr(effect.cond) and is_interpretable(effect.then) and is_interpretable(effect.else_)
    if isinstance(effect, Sequence):
        return all(is_interpretable(i) for i in effect.items)
    if isinstance(effect, Assign):
        return is_pure_expr(effect.target) and is_pure_expr(effect.expr)
    return isinstance(effect, Skip)


class _Return(Exception):
    def __init__(self, value):
        self.value = value


def _wrap(v: int, bits: int | None) -> int:
    return v % (1 << bits) if bits else v


def _expr_struct_type(expr) -> str | None:
    """Resolve the struct type name of a field base (Var → its type; Field → field's type)."""
    if isinstance(expr, Var):
        return _VAR_STRUCT_TYPES.get(expr.name)
    if isinstance(expr, Field):
        inner = _expr_struct_type(expr.base)
        if inner:
            ft = _FIELD_TYPES.get(f"{inner}.{expr.name}")
            if ft and any(k.startswith(f"{ft}.") for k in _FIELD_TYPES):
                return ft
    if isinstance(expr, AddrOf):
        return _expr_struct_type(expr.target)
    if isinstance(expr, Index):
        return _expr_struct_type(expr.base)  # array element = base's pointed-to type
    return None


def _scoped_offset(base, name: str) -> int:
    """Struct-scoped field offset, falling back to the global name for unknown types."""
    struct = _expr_struct_type(base)
    if struct:
        return _SCOPED_OFFSETS.get(f"{struct}.{name}", _FIELD_OFFSETS.get(name, 0))
    return _FIELD_OFFSETS.get(name, 0)


def _lvalue_addr(target, env, bits, mem) -> int:
    """Address of a Field/Index/Deref lvalue in the flat word-addressable memory."""
    if isinstance(target, Field):
        return _eval_expr(target.base, env, bits, mem) + _scoped_offset(target.base, target.name)
    if isinstance(target, Index):
        return _eval_expr(target.base, env, bits, mem) + _eval_expr(target.index, env, bits, mem)
    if isinstance(target, Deref):
        return _eval_expr(target.ptr, env, bits, mem)  # *ptr: the pointer is the address
    return _eval_expr(target, env, bits, mem)


def _eval_expr(e, env, bits=None, mem=None):
    if isinstance(e, IntLit):
        return e.value
    if isinstance(e, BoolLit):
        return e.value
    if isinstance(e, Var):
        return env.get(e.name, 0)  # unknown → 0 (C undefined-identifier / uninit local)
    if isinstance(e, Field):
        addr = _lvalue_addr(e, env, bits, mem)
        return addr if e.name in _EMBEDDED else mem.get(addr, 0) if mem is not None else 0
    if isinstance(e, Index):
        return mem.get(_lvalue_addr(e, env, bits, mem), 0) if mem is not None else 0
    if isinstance(e, Deref):
        addr = _eval_expr(e.ptr, env, bits, mem)
        return mem.get(addr, 0) if mem is not None else 0
    if isinstance(e, Call):
        args = [_eval_expr(a, env, bits, mem) for a in e.args]
        intr = lookup(e.name)
        if intr is not None and (intr.arity is None or len(args) == intr.arity):
            return _eval_intrinsic(intr.op, args, mem)
        if e.name in _BUILTINS:
            return _BUILTINS[e.name](*args)
        if e.name in _FN_TABLE:
            params, effect, callee_bits = _FN_TABLE[e.name]
            return run_effect(effect, {p: v for p, v in zip(params, args)}, callee_bits, mem)
        raise ValueError(f"cannot eval call {e.name}")
    if isinstance(e, BinOp):
        l = _eval_expr(e.left, env, bits, mem)
        r = _eval_expr(e.right, env, bits, mem)
        op = e.op
        if op == "+":
            return _wrap(l + r, bits)
        if op == "-":
            return _wrap(l - r, bits)
        if op == "*":
            return _wrap(l * r, bits)
        if op == "/":
            return l // r
        if op == "%":
            return l % r
        if op == "<<":
            return _wrap(l << (r % bits), bits) if bits else (l << r)
        if op == ">>":
            return (l >> (r % bits)) if bits else (l >> r)
        if op == "&":
            return _wrap(l & r, bits)
        if op == "|":
            return _wrap(l | r, bits)
        if op == "^":
            return _wrap(l ^ r, bits)
        if op == "and":
            return bool(l) and bool(r)
        if op == "or":
            return bool(l) or bool(r)
        raise ValueError(f"unknown binop {op}")
    if isinstance(e, Compare):
        l = _eval_expr(e.left, env, bits, mem)
        r = _eval_expr(e.right, env, bits, mem)
        return {"<": l < r, "<=": l <= r, ">": l > r, ">=": l >= r, "=": l == r, "!=": l != r}[e.op]
    if isinstance(e, Not):
        return not _eval_expr(e.operand, env, bits, mem)
    if isinstance(e, Ternary):
        return (
            _eval_expr(e.then, env, bits, mem)
            if _eval_expr(e.cond, env, bits, mem)
            else _eval_expr(e.else_, env, bits, mem)
        )
    raise ValueError(f"cannot eval {type(e).__name__}")


def _step(effect, env, bits=None, mem=None):
    if isinstance(effect, Return):
        raise _Return(_eval_expr(effect.expr, env, bits, mem) if effect.expr is not None else None)
    if isinstance(effect, Conditional):
        _step(effect.then if _eval_expr(effect.cond, env, bits, mem) else effect.else_, env, bits, mem)
    elif isinstance(effect, Sequence):
        for item in effect.items:
            _step(item, env, bits, mem)
    elif isinstance(effect, Assign):
        value = _eval_expr(effect.expr, env, bits, mem)
        if isinstance(effect.target, Var):
            env[effect.target.name] = value
        else:
            mem[_lvalue_addr(effect.target, env, bits, mem)] = value
    elif isinstance(effect, Skip):
        pass
    else:
        raise ValueError(f"cannot eval effect {type(effect).__name__}")


def run_effect(effect, env, bits=None, mem=None):
    """Evaluate an effect; returns the value of the first ``return`` reached, else None.

    ``bits`` enables C unsigned-wrapping semantics for arithmetic; ``mem`` is an
    optional flat word-addressable memory (dict address → value) for Field/Index
    access. Cell/atomic/pool/MMIO/CLZ masking uses the word width set by
    ``set_word_bits`` (default 32-bit; callers with a type model set it first).
    """
    if mem is None:
        mem = {}
    try:
        _step(effect, dict(env), bits, mem)
        return None
    except _Return as r:
        return r.value


def concrete_inputs(params: list[tuple[str, str]]) -> list[dict[str, int]]:
    """Generate a bounded set of concrete input tuples for a signature."""
    domains = []
    for _, t in params:
        if t in ("Bool",):
            domains.append([0, 1])
        elif t in ("Int", "Nat", "usize", "isize"):
            domains.append([0, 1, 2, 7, 64, 128])
        else:
            domains.append([0])  # opaque handle types → a single probe value
    combos = list(product(*domains))
    if len(combos) > MAX_INPUTS:
        combos = combos[:MAX_INPUTS]
    return [{name: v for (name, _), v in zip(params, combo)} for combo in combos]
