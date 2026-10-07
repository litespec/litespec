"""C expression → LIR ``Expr`` mapping (Phase 2)."""

from __future__ import annotations

import re

from tree_sitter import Node

from litespec.lir.effect_expr_ast import (
    BinOp,
    BoolLit,
    Call,
    Compare,
    Expr,
    Field,
    Index,
    IntLit,
    Not,
    Ternary,
    Var,
)

_BINARY_OPS = {
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "/",
    "%": "%",
    "&&": "and",
    "||": "or",
    "<": "<",
    "<=": "<=",
    ">": ">",
    ">=": ">=",
    "==": "=",
    "!=": "!=",
}


_SIZES: dict[str, int] = {}
_PTR_SIZES: dict[str, int] = {}
_FIELD_OFFSETS: dict[str, int] = {}
_SCOPED_OFFSETS: dict[str, int] = {}
_FIELD_ELEM_SIZES: dict[str, int] = {}


def set_sizes(sizes: dict[str, int]) -> None:
    """Set the type byte-size table used by ``sizeof``."""
    global _SIZES
    _SIZES = dict(sizes)


def set_ptr_sizes(ptr_sizes: dict[str, int]) -> None:
    """Set local/param name → pointed-to struct word size (for pointer arithmetic)."""
    global _PTR_SIZES
    _PTR_SIZES = dict(ptr_sizes)


def get_ptr_sizes() -> dict[str, int]:
    """Return the current struct-pointer → word size table (live view)."""
    return _PTR_SIZES


def set_field_offsets(offsets: dict[str, int]) -> None:
    """Set field name → word offset (for ``&field`` address-of / container_of)."""
    global _FIELD_OFFSETS
    _FIELD_OFFSETS = dict(offsets)


def set_scoped_field_offsets(offsets: dict[str, int]) -> None:
    """Set ``struct.field`` → word offset (for ``offsetof(type, member)``)."""
    global _SCOPED_OFFSETS
    _SCOPED_OFFSETS = dict(offsets)


def set_field_elem_sizes(elem_sizes: dict[str, int]) -> None:
    """Set array field name → element word size (for ``offsetof(type, field[i])``)."""
    global _FIELD_ELEM_SIZES
    _FIELD_ELEM_SIZES = dict(elem_sizes)


def _text(node: Node) -> str:
    return (node.text or b"").decode()


def _child(node: Node, field: str) -> Node | None:
    return node.child_by_field_name(field)


def _find_identifier(node: Node) -> Node | None:
    """Find the first (deepest) ``identifier`` descendant."""
    if node.type == "identifier":
        return node
    for child in node.named_children:
        found = _find_identifier(child)
        if found is not None:
            return found
    return None


def _sizeof_bits(node: Node) -> int | None:
    """Fold the C idiom ``sizeof(T) * 8`` (bits in T) to a word count × 32.

    The memory model's ``sizeof`` returns word counts (1 word = 32 bits), so
    ``sizeof(T) * 8`` (C: bytes × 8) must be ``word_count(T) * 32``.
    """
    op_node = _child(node, "operator")
    if _text(op_node) != "*":
        return None
    left, right = _child(node, "left"), _child(node, "right")
    for sz, n in ((left, right), (right, left)):
        if sz is None or sz.type != "sizeof_expression" or n is None or n.type != "number_literal":
            continue
        try:
            mult = int(_text(n), 0)
        except ValueError:
            continue
        if mult == 8:
            from litespec.extraction.size_table import sizeof_type

            type_node = _child(sz, "type") or _child(sz, "value")
            type_text = _text(type_node) if type_node is not None else ""
            return sizeof_type(type_text, _SIZES) * 32
    return None


def _fold_const(op: str, a: int, b: int) -> int | None:
    """Fold a constant binary expression (literal op literal)."""
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


def map_expression(node: Node | None) -> Expr:
    """Map a C expression node to a LIR ``Expr``."""
    if node is None:
        return Var("null")

    t = node.type

    if t == "null":
        return IntLit(0)  # NULL / nullptr → 0 (pointer→index lowering)

    if t == "sizeof_expression":
        from litespec.extraction.size_table import sizeof_type

        type_node = _child(node, "type")
        if type_node is not None:
            type_text = _text(type_node)
        else:
            # sizeof(typedefName) is parsed as a parenthesized expression, not a type
            value_node = _child(node, "value")
            inner = value_node.named_children[0] if value_node is not None and value_node.named_children else None
            type_text = _text(inner) if inner is not None else (_text(value_node) if value_node is not None else "")
        return IntLit(sizeof_type(type_text, _SIZES))

    if t == "number_literal":
        text = _text(node)
        try:
            return IntLit(int(text, 0))
        except ValueError:
            # strip C integer suffixes (U, L, UL, LL, …) and retry
            stripped = re.sub(r"[uUlL]+$", "", text)
            try:
                return IntLit(int(stripped, 0))
            except ValueError:
                return IntLit(0)

    if t == "identifier":
        text = _text(node)
        if text == "true":
            return BoolLit(True)
        if text == "false":
            return BoolLit(False)
        if text == "TRUE":
            return IntLit(1)  # #define TRUE 1
        if text == "FALSE":
            return IntLit(0)  # #define FALSE 0
        if text in ("NULL", "null", "nullptr"):
            return IntLit(0)
        return Var(text)

    if t in ("true", "false"):
        # tree-sitter misparses the macros TRUE/FALSE as boolean-literal nodes.
        text = _text(node)
        if text in ("TRUE", "FALSE"):
            return IntLit(1 if text == "TRUE" else 0)
        return BoolLit(t == "true")

    if t == "binary_expression":
        bits = _sizeof_bits(node)
        if bits is not None:
            return IntLit(bits)
        left = map_expression(_child(node, "left"))
        op_node = _child(node, "operator")
        op = _text(op_node) if op_node is not None else "+"
        right = map_expression(_child(node, "right"))
        op = _BINARY_OPS.get(op, op)
        if op in ("<", "<=", ">", ">=", "=", "!="):
            return Compare(op, left, right)
        # C pointer arithmetic: `p ± n` (p: struct pointer) → `p ± n*sizeof(struct)`
        if op in ("+", "-") and isinstance(left, Var) and left.name in _PTR_SIZES:
            size = _PTR_SIZES[left.name]
            if size != 1:
                right = BinOp("*", right, IntLit(size))
        # fold constant sub-expressions (e.g. `24 << 3` → 192) so the LIR holds
        # plain IntLits and the Rust lowering never renders a bare-literal receiver.
        if isinstance(left, IntLit) and isinstance(right, IntLit):
            folded = _fold_const(op, left.value, right.value)
            if folded is not None:
                return IntLit(folded)
        return BinOp(op, left, right)

    if t == "unary_expression":
        op_node = _child(node, "operator")
        op = _text(op_node) if op_node is not None else ""
        arg = map_expression(_child(node, "argument"))
        if op == "!":
            return Not(arg)
        if op == "-":
            return BinOp("-", IntLit(0), arg)  # 0 - x (unsigned/wrapping negation)
        if op == "~":
            return BinOp("^", IntLit(-1), arg)  # bitwise NOT: x ^ all-ones
        if op == "&":
            # address-of a field → its address (base + word offset); container_of
            if isinstance(arg, Field):
                return BinOp("+", arg.base, IntLit(_FIELD_OFFSETS.get(arg.name, 0)))
        return arg

    if t == "call_expression":
        fn = _child(node, "function")
        if fn is not None and fn.type == "field_expression":
            # ``obj->method(args)`` → call through the field (flattened name)
            obj = _child(fn, "argument")
            field = _child(fn, "field")
            obj_text = (_text(obj) if obj is not None else "").replace("->", "_")
            field_text = _text(field) if field is not None else ""
            fn_name = f"{obj_text}_{field_text}" if obj_text and field_text else _text(fn)
        else:
            fn_name = (
                _text(_find_identifier(fn))
                if fn is not None and _find_identifier(fn) is not None
                else (_text(fn) if fn else "")
            )
        args_node = _child(node, "arguments")
        args = [map_expression(a) for a in (args_node.named_children if args_node else [])]
        return Call(fn_name, tuple(args))

    if t == "parenthesized_expression":
        return map_expression(node.named_children[0] if node.named_children else None)

    if t == "field_expression":
        obj = _child(node, "argument")
        field = _child(node, "field")
        field_text = _text(field) if field is not None else ""
        return Field(map_expression(obj), field_text)

    if t == "pointer_expression":
        # tree-sitter parses both `*ptr` (deref) and `&x` (address-of) as pointer_expression.
        arg = _child(node, "argument")
        arg_expr = map_expression(arg) if arg is not None else Var(_text(node))
        if _text(node).startswith("&"):
            # address-of: &x → the address of x (field/array/var), rendered via AddrOf.
            from litespec.lir.effect_expr_ast import AddrOf

            return AddrOf(arg_expr)
        from litespec.lir.effect_expr_ast import Deref

        return Deref(arg_expr)

    if t == "subscript_expression":
        arg = _child(node, "argument")
        index = _child(node, "index")
        base = map_expression(arg)
        idx = map_expression(index)
        # struct-pointer array indexing: ptr[i] scales by sizeof(struct)
        if isinstance(base, Var) and base.name in _PTR_SIZES:
            size = _PTR_SIZES[base.name]
            if size != 1:
                idx = BinOp("*", idx, IntLit(size))
        return Index(base, idx)

    if t == "cast_expression":
        type_node = _child(node, "type")
        value_node = _child(node, "value")
        value = map_expression(value_node)
        # (T)x integer cast → widen/narrow via a functional cast Call(T, [x]);
        # pointer/void casts are dropped (the word model has no byte pointers).
        if type_node is not None:
            type_text = _text(type_node)
            if "*" not in type_text and type_text not in ("void", "VOID"):
                return Call(type_text, (value,))
        return value

    if t == "assignment_expression":
        left = map_expression(_child(node, "left"))
        right = map_expression(_child(node, "right"))
        op = _text(_child(node, "operator")) if _child(node, "operator") else "="
        if op == "=":
            return right  # handled by statement_mapping as Assign
        return BinOp(_BINARY_OPS.get(op, op), left, right)

    if t == "conditional_expression":
        children = node.named_children
        if len(children) == 3:
            return Ternary(map_expression(children[0]), map_expression(children[1]), map_expression(children[2]))
        return Var(_text(node))

    if t in ("string_literal", "concatenated_string"):
        return IntLit(0)  # debug strings are opaque; the call itself is preserved

    if t == "char_literal":
        # ``'x'`` / ``'\0'`` / ``'\n'`` → the character's integer value.
        text = _text(node)
        inner = text[1:-1] if len(text) >= 2 else text
        if inner.startswith("\\") and len(inner) > 1:
            esc = inner[1]
            if esc.isdigit():  # octal escape: \0, \12, \377
                return IntLit(int(inner[1:] or "0", 8))
            return IntLit({"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13}.get(esc, ord(esc)))
        return IntLit(ord(inner[0]) if inner else 0)

    if t == "update_expression":
        # x++ / x-- / ++x: map to the variable (the increment side-effect is handled
        # as an Assign when it appears as a statement; in a condition it reads the value).
        # Recurse via ``map_expression`` so field/array targets (``--mutex->muxCount``)
        # stay structured instead of becoming a raw-text Var.
        arg = _child(node, "argument")
        return map_expression(arg) if arg is not None else Var(_text(node))

    if t == "initializer_list":
        # {0} zero-init → 0; {a, b, …} → first element (approximation).
        return map_expression(node.named_children[0]) if node.named_children else IntLit(0)

    if t in ("gnu_asm_expression", "asm_expression", "statement_expression", "compound_statement"):
        # Inline assembly and statement-expressions ``({ … })`` are arch-level side
        # effects outside the word model; treat them as opaque (value 0) rather than
        # falling back to a raw-text Var (which would emit an invalid Rust identifier).
        return IntLit(0)

    # Fallback: an opaque identifier-like atom.
    return Var(_text(node))
