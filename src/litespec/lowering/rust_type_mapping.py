"""LIR ``TypeExpr`` → Rust type mapping (Phase 4).

Primitive mapping is delegated to the *active* type model (set per target); only
the generic ``List``/``Set``/``Map`` containers are handled here.
"""

from __future__ import annotations

from litespec.type_mapping import TypeModel, default_type_model

_TM: TypeModel = default_type_model()


def set_type_model(tm: TypeModel) -> None:
    """Set the active type model used for LIR→Rust primitive mapping."""
    global _TM
    _TM = tm


def int_type() -> str:
    """The port's word type (fixed-width, target-driven), from the active model.

    ``word_bits`` is the single source of truth: ``word_type()`` returns
    ``u{word_bits}`` (``u32`` for LiteOS's 32-bit target, ``u64`` for a 64-bit
    target), and the memory model / handles / arithmetic all use it consistently.
    """
    return _TM.word_type()


def rust_type(type_expr: str) -> str:
    """Map a §7.2 ``TypeExpr`` string to a Rust type."""
    t = type_expr.strip()
    if t.startswith("List<"):
        return f"Vec<{rust_type(t[5:-1])}>"
    if t.startswith("Set<"):
        return f"std::collections::HashSet<{rust_type(t[4:-1])}>"
    if t.startswith("Map<"):
        inner = t[4:-1].split(",", 1)
        return f"std::collections::HashMap<{rust_type(inner[0].strip())}, {rust_type(inner[1].strip())}>"
    return _TM.lir_to_rust_type(t)


def rust_default(type_expr: str) -> str:
    """A default Rust initializer for a type (for pre-declaring state vars)."""
    rt = rust_type(type_expr)
    if rt in ("usize", "isize", "u8", "u16", "u32", "u64", "i8", "i16", "i32", "i64"):
        return "0"
    if rt == "f64":
        return "0.0"
    if rt == "bool":
        return "false"
    if rt == "String":
        return "String::new()"
    if rt == "()":
        return "()"
    return "Default::default()"
