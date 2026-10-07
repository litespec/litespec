"""``EffectExpr`` → Rust emission (Phase 4)."""

from __future__ import annotations

from litespec.intrinsics import Op, lookup
from litespec.lir.effect_expr_ast import (
    AddrOf,
    Assign,
    BinOp,
    BoolLit,
    BreakLabel,
    Call,
    CallEffect,
    Compare,
    Conditional,
    Deref,
    DoWhile,
    EffectExpr,
    Expr,
    ExprStmt,
    Field,
    ForC,
    ForRange,
    Guard,
    Index,
    IntLit,
    Iterator,
    LabeledBlock,
    Let,
    Not,
    Quantified,
    Return,
    Sequence,
    SetUpdate,
    Skip,
    Ternary,
    Var,
    While,
)
from litespec.lowering.rust_type_mapping import int_type, rust_type

_BINARY_OPS = {
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "/",
    "%": "%",
    "and": "&&",
    "or": "||",
}

#: C unsigned arithmetic wraps; these ops lower to wrapping methods so the emitted
#: Rust does not panic on overflow in debug builds. (Shift is handled separately
#: because its RHS is a ``u32`` amount.)
_WRAPPING_METHODS = {"+": "wrapping_add", "-": "wrapping_sub", "*": "wrapping_mul"}

_RUST_KEYWORDS = {
    "as",
    "break",
    "const",
    "continue",
    "crate",
    "dyn",
    "else",
    "enum",
    "extern",
    "false",
    "fn",
    "for",
    "if",
    "impl",
    "in",
    "let",
    "loop",
    "match",
    "mod",
    "move",
    "mut",
    "pub",
    "ref",
    "return",
    "self",
    "Self",
    "static",
    "struct",
    "super",
    "trait",
    "true",
    "type",
    "unsafe",
    "use",
    "where",
    "while",
    "async",
    "await",
    "abstract",
    "become",
    "box",
    "do",
    "final",
    "macro",
    "override",
    "priv",
    "try",
    "typeof",
    "unsized",
    "virtual",
    "yield",
}


def sanitize_ident(name: str) -> str:
    """Return a valid Rust identifier for a C identifier (``r#`` for keywords)."""
    return f"r#{name}" if name in _RUST_KEYWORDS else name


def _fold_const(op: str, a: int, b: int) -> int | None:
    """Fold a constant binary expression (for literal→literal BinOps)."""
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return a // b if b else 0
    if op == "<<":
        return a << b
    if op == ">>":
        return a >> b
    if op == "&":
        return a & b
    if op == "|":
        return a | b
    if op == "^":
        return a ^ b
    return None


_VARIADIC: frozenset[str] = frozenset()
_GLOBALS: frozenset[str] = frozenset()
_CALL_FN_PTR: frozenset[str] = frozenset()
_OFFSETS: dict[str, int] = {}
_SCOPED_OFFSETS: dict[str, int] = {}
_EMBEDDED: frozenset[str] = frozenset()
_CASTS: dict[str, str] = {}
_FIELD_ELEM_SIZES: dict[str, int] = {}
_ADDR_TAKEN: dict[str, int] = {}
_ADDR_SLOT_NEXT = 0x8000
#: union member names that overlap at the union's offset (e.g. ``ptr.prev``/``ptr.next``);
#: derived from the struct table via ``set_union_members``.
_UNION_MEMBERS: frozenset[str] = frozenset()
#: variable name → struct type name (from params/locals), for struct-scoped field offsets.
_VAR_STRUCT_TYPES: dict[str, str] = {}
#: ``struct.field`` → field base type name (for resolving nested ``a->b->c``).
_FIELD_TYPES: dict[str, str] = {}


def set_union_members(names) -> None:
    """Register anonymous-union member names (they overlap at the union's offset)."""
    global _UNION_MEMBERS
    _UNION_MEMBERS = frozenset(names)


def set_variadic(names) -> None:
    """Register variadic function names so their calls render as macro invocations."""
    global _VARIADIC
    _VARIADIC = frozenset(names)


def set_globals(names) -> None:
    """Register global (file-scope) variable names so they render as statics."""
    global _GLOBALS
    _GLOBALS = frozenset(names)


def set_call_fn_ptr(names) -> None:
    """Register function-pointer locals/params so calls render via ``__call_fn_ptr__``."""
    global _CALL_FN_PTR
    _CALL_FN_PTR = frozenset(names)


def set_field_offsets(offsets: dict[str, int]) -> None:
    """Register struct-field word offsets so field access lowers to memory reads/writes."""
    global _OFFSETS
    _OFFSETS = dict(offsets)


def set_scoped_field_offsets(offsets: dict[str, int]) -> None:
    """Register struct-scoped (``struct.field`` → offset) field offsets."""
    global _SCOPED_OFFSETS
    _SCOPED_OFFSETS = dict(offsets)


def set_var_struct_types(types: dict[str, str]) -> None:
    """Register variable name → struct type name (params/locals) for scoped field offsets."""
    global _VAR_STRUCT_TYPES
    _VAR_STRUCT_TYPES = dict(types)


def set_field_types(types: dict[str, str]) -> None:
    """Register ``struct.field`` → field base type name for nested field resolution."""
    global _FIELD_TYPES
    _FIELD_TYPES = dict(types)


def set_embedded_fields(names) -> None:
    """Register embedded sub-struct field names (access yields the sub-struct address)."""
    global _EMBEDDED
    _EMBEDDED = frozenset(names)


def set_casts(names) -> None:
    """Register typedef → Rust type for functional casts (``TYPEDEF(x)`` → ``x as T``)."""
    global _CASTS
    _CASTS = dict(names)


def set_field_elem_sizes(elem_sizes: dict[str, int]) -> None:
    """Register array field name → element word size (for ``array[i]`` scaling)."""
    global _FIELD_ELEM_SIZES
    _FIELD_ELEM_SIZES = dict(elem_sizes)


def set_addr_taken(addr_taken: dict[str, int]) -> None:
    """Register address-taken locals → MEM slot (for ``&local`` output params)."""
    global _ADDR_TAKEN
    _ADDR_TAKEN = dict(addr_taken)


def reset_addr_slots() -> None:
    """Reset the address-taken slot allocator (called once per module)."""
    global _ADDR_SLOT_NEXT
    _ADDR_SLOT_NEXT = 0x8000


def allocate_addr_slots(names: list[str]) -> dict[str, int]:
    """Allocate a fresh MEM slot for each name (address-taken locals)."""
    global _ADDR_SLOT_NEXT
    out = {}
    for name in names:
        out[name] = _ADDR_SLOT_NEXT
        _ADDR_SLOT_NEXT += 1
    return out


def _offset(name: str) -> int:
    return _OFFSETS.get(name, 0)


def _expr_struct_type(expr: Expr) -> str | None:
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


def _scoped_offset(base: Expr, name: str) -> int:
    """Struct-scoped field offset, falling back to the global name for unknown types."""
    struct = _expr_struct_type(base)
    if struct:
        return _SCOPED_OFFSETS.get(f"{struct}.{name}", _OFFSETS.get(name, 0))
    return _OFFSETS.get(name, 0)


def _render_intrinsic(op: Op, args: list[str]) -> str:
    """Rust expression for an intrinsic operation given rendered argument strings."""
    if op is Op.LEADING_ZEROS:
        return f"({args[0]}).leading_zeros()"
    if op is Op.TRAILING_ZEROS:
        return f"({args[0]}).trailing_zeros()"
    if op is Op.FFSL:
        return f"({args[0]}).trailing_zeros().wrapping_add(1{int_type()})"
    if op is Op.ALIGN:
        a = f"(({args[0]}) as {int_type()})"
        b = f"(({args[1]}) as {int_type()})"
        return f"({a}).wrapping_add(({b}).wrapping_sub(1{int_type()})) & !(({b}).wrapping_sub(1{int_type()}))"
    if op is Op.CURR_TASK_GET:
        return "__read_curr_task()"
    if op is Op.CURR_TASK_SET:
        return f"__write_curr_task({args[0]})"
    if op is Op.CURR_CPUID:
        return "__read_curr_cpuid()"
    if op is Op.IDENTITY:
        return args[0]
    if op is Op.ATOMIC_LOAD:
        return f"__read({args[0]})"
    if op is Op.ATOMIC_STORE:
        return f"__write({args[0]}, {args[1]})"
    if op is Op.ATOMIC_ADD:
        return f"__atomic_add({args[0]}, {args[1]})"
    if op is Op.ATOMIC_SUB:
        return f"__atomic_sub({args[0]}, {args[1]})"
    if op is Op.ATOMIC_INC:
        return f"__atomic_add({args[0]}, 1{int_type()})"
    if op is Op.ATOMIC_DEC:
        return f"__atomic_sub({args[0]}, 1{int_type()})"
    if op is Op.ATOMIC_DEC_RET:
        return f"(__atomic_sub({args[0]}, 1{int_type()})).wrapping_sub(1{int_type()})"
    if op is Op.ATOMIC_CMPXCHG:
        return f"__atomic_cmpxchg({args[0]}, {args[1]}, {args[2]})"
    if op is Op.MEM_ALLOC:
        return f"__mem_alloc({args[1]})"
    if op is Op.MEM_ALLOC_ALIGN:
        return f"__mem_alloc_align({args[1]}, {args[2]})"
    if op is Op.MMIO_READ:
        return f"__read_mmio({args[0]})"
    if op is Op.MMIO_WRITE:
        return f"__write_mmio({args[0]}, {args[1]})"
    if op is Op.NOOP:
        return f"0{int_type()}"  # logging/hook helper: discard args
    return f"0{int_type()}"


#: Base address of the flat word model's deterministic bump allocator (word offset).
MEM_POOL_BASE = 0x3000


def memory_model(it: str, *, executable: bool = False, baremetal: bool = False) -> str:
    """Emit the flat word-addressable memory model (RAM + MMIO + memset helpers).

    - Host simulation: RAM is a word-addressable array; MMIO is a separate array.
    - Bare-metal (``baremetal=True``): both RAM and MMIO are volatile device
      accesses (``read_volatile``/``write_volatile``) — no arrays, no ``std``.
    """
    if baremetal:
        return (
            f"// bare-metal memory model: RAM and MMIO are volatile device accesses.\n"
            f"unsafe fn __read(addr: {it}) -> {it} {{ core::ptr::read_volatile(addr as *const {it}) }}\n"
            f"unsafe fn __write(addr: {it}, v: {it}) {{ core::ptr::write_volatile(addr as *mut {it}, v) }}\n"
            f"unsafe fn __read_mmio(addr: {it}) -> {it} {{ core::ptr::read_volatile(addr as *const {it}) }}\n"
            f"unsafe fn __write_mmio(addr: {it}, v: {it}) {{ core::ptr::write_volatile(addr as *mut {it}, v) }}"
        )
    mmio = (
        f"// MMIO (memory-mapped I/O): separate array from RAM (host simulation).\n"
        f"static mut MMIO: [{it}; 65536] = [0; 65536];\n"
        f"unsafe fn __read_mmio(addr: {it}) -> {it} {{ MMIO[addr as usize] }}\n"
        f"unsafe fn __write_mmio(addr: {it}, v: {it}) {{ MMIO[addr as usize] = v; }}"
    )
    model = (
        f"static mut MEM: [{it}; 65536] = [0; 65536];\n"
        f"unsafe fn __read(addr: {it}) -> {it} {{ MEM[addr as usize] }}\n"
        f"unsafe fn __write(addr: {it}, v: {it}) {{ MEM[addr as usize] = v; }}\n"
        f"// current-task cell (abstraction of the CPU's TPIDRPRW register)\n"
        f"static mut CURR_TASK: {it} = 0;\n"
        f"unsafe fn __read_curr_task() -> {it} {{ CURR_TASK }}\n"
        f"unsafe fn __write_curr_task(v: {it}) {{ CURR_TASK = v; }}\n"
        f"// current-CPU-id cell (abstraction of the MPIDR register)\n"
        f"static mut CURR_CPUID: {it} = 0;\n"
        f"unsafe fn __read_curr_cpuid() -> {it} {{ CURR_CPUID }}\n"
        f"unsafe fn __write_curr_cpuid(v: {it}) {{ CURR_CPUID = v; }}\n"
        f"// atomic read-modify-write helpers (single-threaded model)\n"
        f"unsafe fn __atomic_add(addr: {it}, delta: {it}) -> {it} {{ let old = __read(addr); __write(addr, old.wrapping_add(delta)); old }}\n"
        f"unsafe fn __atomic_sub(addr: {it}, delta: {it}) -> {it} {{ let old = __read(addr); __write(addr, old.wrapping_sub(delta)); old }}\n"
        f"unsafe fn __atomic_cmpxchg(addr: {it}, val: {it}, old: {it}) -> {it} {{ if __read(addr) == old {{ __write(addr, val); 1 }} else {{ 0 }} }}\n"
        f"// memory pool: deterministic bump allocator (base + size are word offsets)\n"
        f"static mut POOL_PTR: {it} = {MEM_POOL_BASE};\n"
        f"unsafe fn __mem_alloc(size: {it}) -> {it} {{ let p = POOL_PTR; POOL_PTR = POOL_PTR.wrapping_add(size); p }}\n"
        f"unsafe fn __mem_alloc_align(size: {it}, align: {it}) -> {it} {{ let a = POOL_PTR.wrapping_add(align.wrapping_sub(1)) & !(align.wrapping_sub(1)); POOL_PTR = a.wrapping_add(size); a }}\n"
        f"{mmio}"
    )
    if executable:
        model += (
            f"\nunsafe fn memset(dest: {it}, c: {it}, count: {it}) -> {it} {{ for i in 0..count {{ MEM[(dest + i) as usize] = c; }} 0 }}"
            f"\nunsafe fn memset_s(dest: {it}, _destMax: {it}, c: {it}, count: {it}) -> {it} {{ for i in 0..count {{ MEM[(dest + i) as usize] = c; }} 0 }}"
        )
    return model


def _lvalue(expr: Expr) -> str:
    """Rust expression for the *address* of a Field/Index lvalue."""
    if isinstance(expr, Field):
        # Anonymous-union members overlap at the union's offset (0 within it).
        # e.g. ``node->ptr.prev`` / ``node->ptr.next`` share the ``ptr`` union slot.
        if expr.name in _UNION_MEMBERS and isinstance(expr.base, Field):
            return render_expr_rust(expr.base)
        # An Index base is an array/struct element → its address (not a read).
        base = _lvalue(expr.base) if isinstance(expr.base, Index) else render_expr_rust(expr.base)
        return f"({base} + {_scoped_offset(expr.base, expr.name)})"
    if isinstance(expr, Index):
        # array[i] → base + i * elem_size (word-addressable array indexing)
        if isinstance(expr.base, Field) and expr.base.name in _FIELD_ELEM_SIZES:
            elem = _FIELD_ELEM_SIZES[expr.base.name]
            return f"({render_expr_rust(expr.base)} + ({render_expr_rust(expr.index)}) * {elem})"
        return f"({render_expr_rust(expr.base)} + {render_expr_rust(expr.index)})"
    if isinstance(expr, Deref):
        return render_expr_rust(expr.ptr)  # *ptr: the pointer IS the address
    return render_expr_rust(expr)


def render_expr_rust(expr: Expr) -> str:
    """Map a LIR ``Expr`` to a Rust expression string."""
    if isinstance(expr, BoolLit):
        return "true" if expr.value else "false"
    if isinstance(expr, IntLit):
        if expr.value < 0:
            return f"0{int_type()}.wrapping_sub({abs(expr.value)}{int_type()})"
        return f"{expr.value}"  # bare literal: Rust infers the width from context
    if isinstance(expr, Var):
        if expr.name in _ADDR_TAKEN:
            return f"__read({_ADDR_TAKEN[expr.name]})"  # address-taken local lives in MEM
        return sanitize_ident(expr.name)
    if isinstance(expr, AddrOf):
        if isinstance(expr.target, Var) and expr.target.name in _ADDR_TAKEN:
            return f"{_ADDR_TAKEN[expr.target.name]}"  # &local → its MEM slot
        return _lvalue(expr.target)  # &x → the address of x
    if isinstance(expr, Field):
        if expr.name in _EMBEDDED:
            return _lvalue(expr)  # embedded sub-struct → its address, not a read
        return f"__read({_lvalue(expr)})"
    if isinstance(expr, Index):
        return f"__read({_lvalue(expr)})"
    if isinstance(expr, Deref):
        return f"__read({_lvalue(expr)})"
    if isinstance(expr, Ternary):
        return f"if {_render_condition(expr.cond)} {{ {render_expr_rust(expr.then)} }} else {{ {render_expr_rust(expr.else_)} }}"
    if isinstance(expr, Call):
        intr = lookup(expr.name)
        if intr is not None and (intr.arity is None or len(expr.args) == intr.arity):
            return _render_intrinsic(intr.op, [render_expr_rust(a) for a in expr.args])
        if expr.name in _CASTS and len(expr.args) == 1:
            return f"(({render_expr_rust(expr.args[0])}) as {_CASTS[expr.name]})"  # TYPEDEF(x) → (x as T)
        if expr.name in _GLOBALS:
            # function-pointer global called through an opaque handle
            return f"__call_fn_ptr__({expr.name})"
        if expr.name in _CALL_FN_PTR:
            # function-pointer param/local called through an opaque handle
            return f"__call_fn_ptr__({expr.name})"
        args = ", ".join(render_expr_rust(a) for a in expr.args)
        if expr.name in _VARIADIC:
            return f"{expr.name}!({args})"
        return f"{expr.name}({args})"
    if isinstance(expr, Not):
        # C logical NOT yields an integer 0/1 in value position.
        return f"((!({_render_condition(expr.operand)})) as {int_type()})"
    if isinstance(expr, Compare):
        op = "==" if expr.op == "=" else expr.op
        # C comparison yields an integer 0/1 (not a Rust bool) in value position.
        return f"(({render_expr_rust(expr.left)}) {op} ({render_expr_rust(expr.right)})) as {int_type()}"
    if isinstance(expr, BinOp):
        if expr.op == "implies":
            return f"((!({_render_condition(expr.left)})) || ({_render_condition(expr.right)})) as {int_type()}"
        if expr.op in ("and", "or"):
            op = _BINARY_OPS[expr.op]
            return f"(({_render_condition(expr.left)}) {op} ({_render_condition(expr.right)})) as {int_type()}"
        # Fold constant sub-expressions (e.g. ``1 << 3``) so a bare literal never
        # becomes a wrapping-method *receiver* (Rust cannot infer its type).
        if isinstance(expr.left, IntLit) and isinstance(expr.right, IntLit):
            folded = _fold_const(expr.op, expr.left.value, expr.right.value)
            if folded is not None:
                return render_expr_rust(IntLit(folded))
        if expr.op == "<<":
            if isinstance(expr.left, IntLit):
                return f"({expr.left.value}{int_type()}).wrapping_shl(({render_expr_rust(expr.right)}) as u32)"
            return f"({render_expr_rust(expr.left)}).wrapping_shl(({render_expr_rust(expr.right)}) as u32)"
        if expr.op in _WRAPPING_METHODS:
            l, r = expr.left, expr.right
            # avoid a bare-literal *receiver* (Rust cannot infer its type in a method call):
            # swap commutative ops, or use `l - r == -r + l` for subtraction.
            if isinstance(l, IntLit) and l.value >= 0 and not isinstance(r, IntLit):
                if expr.op in ("+", "*", "&", "|", "^"):
                    return f"({render_expr_rust(r)}).{_WRAPPING_METHODS[expr.op]}({render_expr_rust(l)})"
                if expr.op == "-":
                    return f"({render_expr_rust(r)}).wrapping_neg().wrapping_add({render_expr_rust(l)})"
            return f"({render_expr_rust(l)}).{_WRAPPING_METHODS[expr.op]}({render_expr_rust(r)})"
        op = _BINARY_OPS.get(expr.op, expr.op)
        return f"({render_expr_rust(expr.left)} {op} {render_expr_rust(expr.right)})"
    return str(expr)


def _render_condition(expr: Expr) -> str:
    """Render an expression in boolean position (C integers → Rust bool)."""
    if isinstance(expr, IntLit):
        return "true" if expr.value != 0 else "false"
    if isinstance(expr, Compare):
        op = "==" if expr.op == "=" else expr.op
        return f"{render_expr_rust(expr.left)} {op} {render_expr_rust(expr.right)}"
    if isinstance(expr, BoolLit):
        return "true" if expr.value else "false"
    if isinstance(expr, Not):
        return f"!({_render_condition(expr.operand)})"
    if isinstance(expr, BinOp) and expr.op in ("and", "or"):
        op = _BINARY_OPS[expr.op]
        return f"({_render_condition(expr.left)}) {op} ({_render_condition(expr.right)})"
    if isinstance(expr, BinOp) and expr.op == "implies":
        return f"(!({_render_condition(expr.left)})) || ({_render_condition(expr.right)})"
    return f"({render_expr_rust(expr)}) != 0"  # C: nonzero is true


class RustEmitter:
    """Renders an ``EffectExpr`` to Rust, tracking declared local variables."""

    def __init__(self, types: dict[str, str], declared: set[str] | None = None):
        self.types = types
        self.declared = set(declared or set())

    def _indent(self, depth: int) -> str:
        return "    " * depth

    def _decl_type(self, name: str) -> str:
        return rust_type(self.types.get(name, "Nat"))

    def render(self, effect: EffectExpr, depth: int = 0) -> list[str]:
        ind = self._indent(depth)
        lines: list[str] = []

        if isinstance(effect, Skip):
            return []
        if isinstance(effect, ExprStmt):
            if isinstance(effect.expr, Var):
                name = effect.expr.name
                if name == "__break__":
                    lines.append(f"{ind}break;")
                elif name == "__continue__":
                    lines.append(f"{ind}continue;")
                elif name.startswith("__goto_"):
                    lines.append(f"{ind}// goto {name[7:]} (goto elimination TODO)")
                elif name.startswith("__label_"):
                    lines.append(f"{ind}// label {name[8:]}:")
                else:
                    lines.append(f"{ind}{render_expr_rust(effect.expr)};")
            else:
                lines.append(f"{ind}{render_expr_rust(effect.expr)};")
        elif isinstance(effect, Assign):
            target = effect.target
            if isinstance(target, Var):
                if target.name in _ADDR_TAKEN:
                    # address-taken local → memory write
                    lines.append(f"{ind}__write({_ADDR_TAKEN[target.name]}, {render_expr_rust(effect.expr)});")
                else:
                    name = sanitize_ident(target.name)
                    if target.name in self.declared or target.name in _GLOBALS:
                        lines.append(f"{ind}{name} = {render_expr_rust(effect.expr)};")
                    else:
                        self.declared.add(target.name)
                        lines.append(
                            f"{ind}let mut {name}: {self._decl_type(target.name)} = {render_expr_rust(effect.expr)};"
                        )
            else:
                # Field/Index/Deref lvalue → memory write
                lines.append(f"{ind}__write({_lvalue(target)}, {render_expr_rust(effect.expr)});")
        elif isinstance(effect, SetUpdate):
            lines.append(f"{ind}// set update {effect.target} (lowering TODO)")
        elif isinstance(effect, Conditional):
            lines.append(f"{ind}if {_render_condition(effect.cond)} {{")
            lines.extend(self.render(effect.then, depth + 1))
            lines.append(f"{ind}}} else {{")
            lines.extend(self.render(effect.else_, depth + 1))
            lines.append(f"{ind}}}")
        elif isinstance(effect, While):
            lines.append(f"{ind}while {_render_condition(effect.cond)} {{")
            lines.extend(self.render(effect.body, depth + 1))
            lines.append(f"{ind}}}")
        elif isinstance(effect, Let):
            ty = rust_type(effect.type)
            lines.append(f"{ind}{{")
            lines.append(f"{self._indent(depth + 1)}let {effect.name}: {ty} = {{")
            lines.extend(self.render(effect.value, depth + 2))
            lines.append(f"{self._indent(depth + 1)}}};")
            lines.extend(self.render(effect.body, depth + 1))
            lines.append(f"{ind}}}")
        elif isinstance(effect, Quantified):
            lines.append(f"{ind}// quantified {effect.quantifier} {effect.name} (lowering TODO)")
            lines.extend(self.render(effect.body, depth))
        elif isinstance(effect, Sequence):
            for item in effect.items:
                lines.extend(self.render(item, depth))
        elif isinstance(effect, ForRange) or isinstance(effect, Iterator):
            lines.append(f"{ind}for {effect.name} in {render_expr_rust(effect.iterable)} {{")
            lines.extend(self.render(effect.body, depth + 1))
            lines.append(f"{ind}}}")
        elif isinstance(effect, ForC):
            lines.extend(self.render(effect.init, depth))
            lines.append(f"{ind}while {_render_condition(effect.guard)} {{")
            lines.extend(self.render(effect.body, depth + 1))
            lines.extend(self.render(effect.step, depth + 1))
            lines.append(f"{ind}}}")
        elif isinstance(effect, DoWhile):
            lines.append(f"{ind}loop {{")
            lines.extend(self.render(effect.body, depth + 1))
            lines.append(f"{self._indent(depth + 1)}if !({_render_condition(effect.cond)}) {{ break; }}")
            lines.append(f"{ind}}}")
        elif isinstance(effect, BreakLabel):
            lines.append(f"{ind}break '{effect.name};")
        elif isinstance(effect, LabeledBlock):
            lines.append(f"{ind}'{effect.name}: {{")
            lines.extend(self.render(effect.body, depth + 1))
            lines.append(f"{ind}}}")
        elif isinstance(effect, CallEffect):
            args = ", ".join(render_expr_rust(a) for a in effect.args)
            lines.append(f"{ind}{effect.name}({args});")
        elif isinstance(effect, Guard):
            lines.append(f"{ind}assert!({_render_condition(effect.cond)});")
        elif isinstance(effect, Return):
            if effect.expr is not None:
                lines.append(f"{ind}return {render_expr_rust(effect.expr)};")
            else:
                lines.append(f"{ind}return;")
        return lines


def addr_taken_vars(effect: EffectExpr) -> set[str]:
    """Collect locals/params whose address is taken (``&x``) in an effect."""
    import dataclasses

    names: set[str] = set()

    def walk(obj):
        if isinstance(obj, AddrOf) and isinstance(obj.target, Var):
            names.add(obj.target.name)
        elif isinstance(obj, (EffectExpr, Expr)):
            for f in dataclasses.fields(obj):
                walk(getattr(obj, f.name))
        elif isinstance(obj, (list, tuple)):
            for x in obj:
                walk(x)

    walk(effect)
    return names


def assigned_targets(effect: EffectExpr) -> set[str]:
    """Collect the set of ``Assign`` targets in an effect (for ``mut`` params)."""
    targets: set[str] = set()

    def walk(e: EffectExpr) -> None:
        if isinstance(e, Assign):
            if isinstance(e.target, Var):
                targets.add(e.target.name)
        elif isinstance(e, Sequence):
            for item in e.items:
                walk(item)
        elif isinstance(e, Conditional):
            walk(e.then)
            walk(e.else_)
        elif isinstance(e, (While, ForRange, Iterator, DoWhile)):
            walk(e.body)
        elif isinstance(e, ForC):
            walk(e.init)
            walk(e.step)
            walk(e.body)
        elif isinstance(e, Let):
            walk(e.value)
            walk(e.body)
        elif isinstance(e, Quantified) or isinstance(e, LabeledBlock):
            walk(e.body)

    walk(effect)
    return targets


def render_effect_rust(effect: EffectExpr, types: dict[str, str], declared: set[str] | None = None) -> str:
    """Render an ``EffectExpr`` to Rust, declaring locals on first assignment."""
    emitter = RustEmitter(types, declared=declared)
    return "\n".join(emitter.render(effect))
