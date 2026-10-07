"""C statement → LIR ``EffectExpr`` mapping (Phase 2)."""

from __future__ import annotations

from tree_sitter import Node

from litespec.extraction.expression_mapping import _child, _find_identifier, _text, get_ptr_sizes, map_expression
from litespec.lir.effect_expr_ast import (
    Assign,
    BinOp,
    BoolLit,
    Conditional,
    DoWhile,
    EffectExpr,
    ExprStmt,
    Field,
    ForC,
    Index,
    IntLit,
    Return,
    Sequence,
    Skip,
    Var,
    While,
)

#: Active macro table (set by ``extract_function``) for for-loop statement-macro detection.
_MACROS = None


def set_macros(macros) -> None:
    """Register the active macro table so ``map_statement`` can expand for-loop macros."""
    global _MACROS
    _MACROS = macros


def _target_text(node: Node | None) -> str:
    """Assignment-target name, normalizing ``->`` to ``.``."""
    if node is None:
        return ""
    return _text(node).replace("->", ".").replace("*", "").strip()


def _target_expr(node: Node | None) -> EffectExpr:
    """Assignment-target lvalue as a structured ``Var``/``Field``/``Index``."""
    if node is None:
        return Var("")
    t = node.type
    if t == "identifier":
        return Var(_text(node))
    if t == "call_expression":
        # ``f()->field = …`` — the base is a call result, keep it as a Call
        # (a raw-text Var here would leak ``f()`` into the constant stubs).
        return map_expression(node)
    if t == "field_expression":
        arg = _child(node, "argument")
        field = _child(node, "field")
        return Field(_target_expr(arg), _text(field) if field is not None else "")
    if t == "subscript_expression":
        arg = _child(node, "argument")
        index = _child(node, "index")
        base = _target_expr(arg)
        idx = map_expression(index)
        # struct-pointer array indexing: ptr[i] scales by sizeof(struct)
        if isinstance(base, Var) and base.name in get_ptr_sizes():
            size = get_ptr_sizes()[base.name]
            if size != 1:
                idx = BinOp("*", idx, IntLit(size))
        return Index(base, idx)
    if t == "cast_expression":
        value = _child(node, "value")
        return _target_expr(value) if value is not None else Var("")
    if t in ("pointer_expression", "unary_expression"):
        arg = _child(node, "argument") or (node.named_children[0] if node.named_children else None)
        return Index(map_expression(arg), IntLit(0))  # *addr = v ⇔ addr[0] = v
    if t == "parenthesized_expression":
        return _target_expr(node.named_children[0] if node.named_children else None)
    return Var(_target_text(node))


def _label_name(node: Node) -> str:
    for child in node.named_children:
        if child.type == "statement_identifier":
            return _text(child)
    return ""


_COMPOUND_OPS = {
    "+=": "+",
    "-=": "-",
    "*=": "*",
    "/=": "/",
    "%=": "%",
    "<<=": "<<",
    ">>=": ">>",
    "&=": "&",
    "|=": "|",
    "^=": "^",
}


def _map_step(node: Node) -> EffectExpr:
    """Map a for-loop init/update expression (assignment or ++/--) to an effect."""
    t = node.type
    if t == "assignment_expression":
        left = _child(node, "left")
        op_node = _child(node, "operator")
        op = _text(op_node) if op_node is not None else "="
        right = map_expression(_child(node, "right"))
        target = _target_expr(left)
        if op == "=":
            return Assign(target, right)
        return Assign(target, BinOp(_COMPOUND_OPS.get(op, op), target, right))
    if t == "update_expression":
        arg = _child(node, "argument")
        op_node = _child(node, "operator")
        op = _text(op_node) if op_node is not None else "++"
        target = _target_expr(arg)
        delta = IntLit(1 if op == "++" else -1)
        return Assign(target, BinOp("+", target, delta))
    if t == "comma_expression":
        # ``for (…; …; index++, swtmr++)`` — map each sub-step and sequence them.
        steps = [_map_step(c) for c in node.named_children]
        return Sequence(tuple(steps)) if len(steps) > 1 else (steps[0] if steps else Skip())
    return ExprStmt(map_expression(node))


def map_declaration(node: Node) -> list[EffectExpr]:
    """Map a C declaration (with optional initializers) to assignments."""
    effects: list[EffectExpr] = []
    for child in node.named_children:
        if child.type == "init_declarator":
            declarator = _child(child, "declarator")
            value = _child(child, "value")
            name = _find_identifier(declarator)
            if name is not None and value is not None:
                effects.append(Assign(Var(_text(name)), map_expression(value)))
    return effects


def _map_for(node: Node, config=None) -> EffectExpr:
    init_node = _child(node, "initializer")
    cond_node = _child(node, "condition")
    update_node = _child(node, "update")
    body_node = _child(node, "body")

    binder_name = "i"
    binder_type = "Nat"
    init_effect: EffectExpr = Skip()

    if init_node is not None:
        if init_node.type == "declaration":
            name = _find_identifier(init_node)
            if name is not None:
                binder_name = _text(name)
            init_effects = map_declaration(init_node)
            init_effect = init_effects[0] if init_effects else Skip()
        elif init_node.type in ("assignment_expression", "update_expression"):
            init_effect = _map_step(init_node)
            left = _child(init_node, "left") or _child(init_node, "argument")
            if left is not None:
                binder_name = _target_text(left)
        else:
            init_effect = ExprStmt(map_expression(init_node))

    guard = map_expression(cond_node) if cond_node is not None else BoolLit(True)
    step = _map_step(update_node) if update_node is not None else Skip()
    body = Sequence(tuple(map_statement(body_node, config)))
    return ForC(binder_name, binder_type, init_effect, guard, step, body)


def _map_preproc(node: Node, config) -> list[EffectExpr]:
    """Map a ``#if`` / ``#ifdef`` / ``#ifndef`` block, selecting the active branch."""
    from litespec.extraction.config import Config, eval_pp_condition

    if config is None:
        config = Config()

    if node.type == "preproc_ifdef":
        # tree-sitter parses both #ifdef and #ifndef as `preproc_ifdef`; distinguish
        # by the directive keyword text.
        name = _text(node.child_by_field_name("name"))
        directive = _text(node).lstrip().split(None, 1)[0] if _text(node).strip() else ""
        active = (not config.is_defined(name)) if directive == "#ifndef" else config.is_defined(name)
    else:  # preproc_if
        expr = _text(node.child_by_field_name("condition"))
        active = eval_pp_condition(expr, config)

    cond_node = node.child_by_field_name("name") or node.child_by_field_name("condition")
    effects: list[EffectExpr] = []
    in_else = False
    for child in node.named_children:
        if child is cond_node:
            continue
        if child.type == "preproc_else":
            in_else = True
            if not active:
                for c in child.named_children:
                    effects.extend(map_statement(c, config))
            continue
        if active and not in_else:
            effects.extend(map_statement(child, config))
    return effects


def _map_switch(node: Node, config=None) -> list[EffectExpr]:
    """Map a ``switch`` to a nested ``Conditional`` (if/else-if chain).

    Fall-through ``case a: case b: stmt`` becomes ``(cond == a) || (cond == b)``;
    ``default`` becomes the final ``else`` branch.
    """
    from litespec.lir.effect_expr_ast import Compare, Skip

    cond = map_expression(_child(node, "condition"))
    body = _child(node, "body")

    # Collect (value_or_None, statements) per case label.
    cases: list[tuple[object | None, list[EffectExpr]]] = []
    for c in body.named_children if body else []:
        if c.type != "case_statement":
            continue
        value_node = _child(c, "value")
        value = map_expression(value_node) if value_node is not None else None
        stmts: list[EffectExpr] = []
        for s in c.named_children:
            if s is value_node:
                continue
            stmts.extend(map_statement(s, config))
        # drop switch-exit ``break`` (the if/else chain already falls through)
        stmts = [
            e
            for e in stmts
            if not (
                isinstance(e, ExprStmt) and isinstance(e.expr, Var) and e.expr.name in ("__break__", "__continue__")
            )
        ]
        cases.append((value, stmts))

    # Propagate statements backward for fall-through (empty non-default case).
    for i in range(len(cases) - 2, -1, -1):
        if not cases[i][1] and cases[i][0] is not None:
            cases[i] = (cases[i][0], cases[i + 1][1])

    # Group consecutive non-default cases with identical statements (fall-through).
    grouped: list[tuple[list[object], list[EffectExpr]]] = []
    default_stmts: list[EffectExpr] = []
    for value, stmts in cases:
        if value is None:
            default_stmts = stmts
        elif grouped and grouped[-1][1] == stmts:
            grouped[-1][0].append(value)
        else:
            grouped.append(([value], stmts))

    def _or_cond(values: list[object]):
        conds = [Compare("=", cond, v) for v in values]
        out = conds[0]
        for c in conds[1:]:
            out = BinOp("or", out, c)
        return out

    # Build the nested Conditional from the last group back to the first.
    tail: EffectExpr = Sequence(tuple(default_stmts)) if default_stmts else Skip()
    for values, stmts in reversed(grouped):
        branch = Conditional(_or_cond(values), Sequence(tuple(stmts)), tail)
        tail = branch
    return [tail]


def _is_for_macro_stmt(node: Node) -> bool:
    """True if ``node`` is a call to a macro whose body is a ``for (…)`` header."""
    if _MACROS is None or node.type != "expression_statement":
        return False
    inner = node.named_children[0] if node.named_children else None
    if inner is None or inner.type != "call_expression":
        return False
    fn = _child(inner, "function")
    name = _text(fn) if fn is not None else ""
    return name in _MACROS.functions and _MACROS.functions[name][1].lstrip().startswith("for")


def _expand_for_macro_at_map(call, macros, body: EffectExpr) -> EffectExpr:
    """Expand a for-loop statement-macro (``LOS_DL_LIST_FOR_EACH_ENTRY(x) { … }``).

    The macro body is a ``for (init; cond; step)`` header; ``body`` is the ``{ … }``
    block that follows the call in the source.
    """
    import re

    from litespec.extraction.c_parser import parse_c
    from litespec.extraction.macro_resolution import _expr_to_c_text, _find_for

    params, body_text = macros.functions[call.name]
    text = body_text
    for p, a in zip(params, call.args):
        text = re.sub(r"\b" + re.escape(p) + r"\b", lambda _m: _expr_to_c_text(a), text)
    node = _find_for(parse_c(text.encode()))
    if node is None:
        return ExprStmt(call)
    for_effect = _map_for(node)
    if isinstance(for_effect, ForC):
        return ForC(for_effect.name, for_effect.type, for_effect.init, for_effect.guard, for_effect.step, body)
    return for_effect


def map_statement(node: Node | None, config=None) -> list[EffectExpr]:
    """Map a C statement node to a list of ``EffectExpr`` (a statement may desugar)."""
    if node is None:
        return []

    t = node.type

    if t in ("preproc_if", "preproc_ifdef", "preproc_ifndef"):
        return _map_preproc(node, config)

    if t == "compound_statement":
        effects: list[EffectExpr] = []
        children = node.named_children
        i = 0
        while i < len(children):
            child = children[i]
            # A for-loop statement-macro ``MACRO(x) { … }``: the call expands to a
            # ``for`` header and the *next* compound_statement is the loop body.
            if _is_for_macro_stmt(child) and i + 1 < len(children) and children[i + 1].type == "compound_statement":
                inner = child.named_children[0]
                call = map_expression(inner)
                body = Sequence(tuple(map_statement(children[i + 1], config)))
                effects.append(_expand_for_macro_at_map(call, _MACROS, body))
                i += 2
            else:
                effects.extend(map_statement(child, config))
                i += 1
        return effects

    if t == "expression_statement":
        inner = node.named_children[0] if node.named_children else None
        if inner is not None and inner.type in ("assignment_expression", "update_expression"):
            return [_map_step(inner)]  # x = …, x += …, ++x, x-- → Assign
        return [ExprStmt(map_expression(inner))]

    if t == "declaration":
        return map_declaration(node)

    if t == "if_statement":
        cond = map_expression(_child(node, "condition"))
        then = Sequence(tuple(map_statement(_child(node, "consequence"), config)))
        alt = _child(node, "alternative")
        if alt is not None:
            if alt.type == "else_clause":
                alt = alt.named_children[0] if alt.named_children else None
            else_ = Sequence(tuple(map_statement(alt, config)))
        else:
            else_ = Skip()
        return [Conditional(cond, then, else_)]

    if t == "while_statement":
        cond = map_expression(_child(node, "condition"))
        body = Sequence(tuple(map_statement(_child(node, "body"), config)))
        return [While(cond, body)]

    if t == "for_statement":
        return [_map_for(node, config)]

    if t == "do_statement":
        body = Sequence(tuple(map_statement(_child(node, "body"), config)))
        cond = map_expression(_child(node, "condition"))
        return [DoWhile(body, cond)]

    if t == "return_statement":
        arg = map_expression(node.named_children[0]) if node.named_children else None
        return [Return(arg)]

    if t == "switch_statement":
        return _map_switch(node, config)

    if t == "break_statement":
        return [ExprStmt(Var("__break__"))]  # desugared into exit-state by D76 (follow-up)

    if t == "continue_statement":
        return [ExprStmt(Var("__continue__"))]

    if t == "goto_statement":
        return [ExprStmt(Var(f"__goto_{_label_name(node)}"))]

    if t == "labeled_statement":
        label = _label_name(node)
        body_node = node.named_children[-1] if len(node.named_children) > 1 else None
        return [ExprStmt(Var(f"__label_{label}"))] + map_statement(body_node, config)

    return []


def map_function_body(body_node: Node | None, config=None) -> EffectExpr:
    """Map a function body (compound_statement) to a single ``EffectExpr``."""
    effects = map_statement(body_node, config)
    if not effects:
        return Skip()
    if len(effects) == 1:
        return effects[0]
    return Sequence(tuple(effects))
