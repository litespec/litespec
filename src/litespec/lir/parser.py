"""Hand-written recursive-descent parser for the EffectExpr grammar (§7.5).

Produces the frozen :mod:`litespec.lir.effect_expr_ast` nodes. The normative
grammar is documented in :file:`grammar.lark`.
"""

from __future__ import annotations

from dataclasses import dataclass

from litespec.lir.effect_expr_ast import (
    Assign,
    BinOp,
    BoolLit,
    Call,
    CallEffect,
    Compare,
    Conditional,
    DoWhile,
    EffectExpr,
    Expr,
    ExprStmt,
    ForC,
    ForRange,
    Guard,
    IntLit,
    Iterator,
    Let,
    Not,
    Quantified,
    Return,
    Sequence,
    SetUpdate,
    Skip,
    Var,
    While,
)

_KEYWORDS = {
    "if",
    "then",
    "else",
    "let",
    "in",
    "seq",
    "while",
    "do",
    "od",
    "for",
    "exists",
    "forall",
    "iterator",
    "call",
    "guard",
    "return",
    "skip",
    "not",
    "and",
    "or",
    "implies",
    "true",
    "false",
}


@dataclass(frozen=True)
class Token:
    kind: str  # "ident" | "int" | "sym"
    value: str
    pos: int


def _tokenize(text: str) -> list[Token]:
    toks: list[Token] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c.isspace() or c == "\n":
            i += 1
            continue
        if c.isalpha() or c == "_":
            j = i
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            toks.append(Token("ident", text[i:j], i))
            i = j
            continue
        if c.isdigit():
            j = i
            while j < n and text[j].isdigit():
                j += 1
            toks.append(Token("int", text[i:j], i))
            i = j
            continue
        if text[i : i + 2] in ("<=", ">=", "!="):
            toks.append(Token("sym", text[i : i + 2], i))
            i += 2
            continue
        toks.append(Token("sym", c, i))
        i += 1
    toks.append(Token("sym", "<EOF>", n))
    return toks


class _Parser:
    def __init__(self, text: str):
        self.toks = _tokenize(text)
        self.i = 0

    def peek(self, offset: int = 0) -> Token:
        j = min(self.i + offset, len(self.toks) - 1)
        return self.toks[j]

    def advance(self) -> Token:
        t = self.toks[self.i]
        if self.i < len(self.toks) - 1:
            self.i += 1
        return t

    def accept_sym(self, s: str) -> bool:
        if self.peek().kind == "sym" and self.peek().value == s:
            self.advance()
            return True
        return False

    def expect_sym(self, s: str) -> None:
        if not self.accept_sym(s):
            raise ValueError(f"expected {s!r} at position {self.peek().pos}, got {self.peek().value!r}")

    def accept_kw(self, kw: str) -> bool:
        t = self.peek()
        if t.kind == "ident" and t.value == kw:
            self.advance()
            return True
        return False

    def expect_kw(self, kw: str) -> None:
        if not self.accept_kw(kw):
            raise ValueError(f"expected {kw!r} at position {self.peek().pos}")

    def expect_ident(self) -> str:
        t = self.peek()
        if t.kind != "ident":
            raise ValueError(f"expected identifier at position {t.pos}, got {t.value!r}")
        self.advance()
        return t.value

    # ---- expressions --------------------------------------------------- #

    def parse_expr(self) -> Expr:
        return self._parse_implies()

    def _parse_implies(self) -> Expr:
        left = self._parse_or()
        while self.accept_kw("implies"):
            left = BinOp("implies", left, self._parse_or())
        return left

    def _parse_or(self) -> Expr:
        left = self._parse_and()
        while self.accept_kw("or"):
            left = BinOp("or", left, self._parse_and())
        return left

    def _parse_and(self) -> Expr:
        left = self._parse_compare()
        while self.accept_kw("and"):
            left = BinOp("and", left, self._parse_compare())
        return left

    def _parse_compare(self) -> Expr:
        left = self._parse_add()
        t = self.peek()
        if t.kind == "sym" and t.value in ("<", "<=", ">", ">=", "=", "!="):
            op = self.advance().value
            return Compare(op, left, self._parse_add())
        return left

    def _parse_add(self) -> Expr:
        left = self._parse_mul()
        while self.peek().kind == "sym" and self.peek().value in ("+", "-"):
            op = self.advance().value
            left = BinOp(op, left, self._parse_mul())
        return left

    def _parse_mul(self) -> Expr:
        left = self._parse_unary()
        while self.peek().kind == "sym" and self.peek().value in ("*", "/"):
            op = self.advance().value
            left = BinOp(op, left, self._parse_unary())
        return left

    def _parse_unary(self) -> Expr:
        if self.accept_kw("not"):
            return Not(self._parse_unary())
        return self._parse_primary()

    def _parse_primary(self) -> Expr:
        t = self.peek()
        if self.accept_kw("true"):
            return BoolLit(True)
        if self.accept_kw("false"):
            return BoolLit(False)
        if t.kind == "int":
            self.advance()
            return IntLit(int(t.value))
        if t.kind == "ident":
            name = self.advance().value
            if self.peek().kind == "sym" and self.peek().value == "(":
                self.advance()
                args: list[Expr] = []
                if not (self.peek().kind == "sym" and self.peek().value == ")"):
                    while True:
                        args.append(self.parse_expr())
                        if self.accept_sym(","):
                            continue
                        break
                self.expect_sym(")")
                return Call(name, tuple(args))
            return Var(name)
        if self.accept_sym("("):
            e = self.parse_expr()
            self.expect_sym(")")
            return e
        raise ValueError(f"unexpected token {t.value!r} at position {t.pos}")

    # ---- effects ------------------------------------------------------- #

    def parse_effect(self) -> EffectExpr:
        t = self.peek()
        if t.kind == "ident":
            kw = t.value
            if kw == "if":
                return self._parse_if()
            if kw == "let":
                return self._parse_let()
            if kw in ("exists", "forall"):
                return self._parse_quantified()
            if kw == "seq":
                return self._parse_seq()
            if kw == "while":
                return self._parse_while()
            if kw == "for":
                return self._parse_for()
            if kw == "do":
                return self._parse_do_while()
            if kw == "iterator":
                return self._parse_iterator()
            if kw == "call":
                return self._parse_call_effect()
            if kw == "guard":
                return self._parse_guard()
            if kw == "return":
                return self._parse_return()
            if kw == "skip":
                self.advance()
                return Skip()
        return self._parse_simple()

    def _parse_if(self) -> Conditional:
        self.expect_kw("if")
        cond = self.parse_expr()
        self.expect_kw("then")
        then = self.parse_effect()
        self.expect_kw("else")
        else_ = self.parse_effect()
        return Conditional(cond, then, else_)

    def _parse_let(self) -> Let:
        self.expect_kw("let")
        name = self.expect_ident()
        self.expect_sym(":")
        typ = self.expect_ident()
        self.expect_sym("=")
        value = self.parse_effect()
        self.expect_kw("in")
        body = self.parse_effect()
        return Let(name, typ, value, body)

    def _parse_quantified(self) -> Quantified:
        q = self.advance().value
        name = self.expect_ident()
        self.expect_sym(":")
        typ = self.expect_ident()
        self.expect_kw("in")
        domain = self.expect_ident()
        self.expect_sym(",")
        body = self.parse_effect()
        return Quantified(q, name, typ, domain, body)

    def _parse_seq(self) -> Sequence:
        self.expect_kw("seq")
        self.expect_sym("{")
        items: list[EffectExpr] = []
        if not (self.peek().kind == "sym" and self.peek().value == "}"):
            while True:
                items.append(self.parse_effect())
                if self.accept_sym(";"):
                    continue
                break
        self.expect_sym("}")
        return Sequence(tuple(items))

    def _parse_while(self) -> While:
        self.expect_kw("while")
        cond = self.parse_expr()
        self.expect_kw("do")
        body = self.parse_effect()
        self.expect_kw("od")
        return While(cond, body)

    def _parse_for(self) -> EffectExpr:
        self.expect_kw("for")
        name = self.expect_ident()
        self.expect_sym(":")
        typ = self.expect_ident()
        if self.accept_sym("="):
            # ForCExpr: for x : T = init ; guard ; step do body od
            init = self.parse_effect()
            self.expect_sym(";")
            guard = self.parse_expr()
            self.expect_sym(";")
            step = self.parse_effect()
            self.expect_kw("do")
            body = self.parse_effect()
            self.expect_kw("od")
            return ForC(name, typ, init, guard, step, body)
        self.expect_kw("in")
        iterable = self.parse_expr()
        self.expect_kw("do")
        body = self.parse_effect()
        self.expect_kw("od")
        return ForRange(name, typ, iterable, body)

    def _parse_do_while(self) -> DoWhile:
        self.expect_kw("do")
        body = self.parse_effect()
        self.expect_kw("while")
        cond = self.parse_expr()
        self.expect_kw("od")
        return DoWhile(body, cond)

    def _parse_iterator(self) -> Iterator:
        self.expect_kw("iterator")
        name = self.expect_ident()
        self.expect_sym(":")
        typ = self.expect_ident()
        self.expect_kw("in")
        iterable = self.parse_expr()
        self.expect_kw("do")
        body = self.parse_effect()
        self.expect_kw("od")
        return Iterator(name, typ, iterable, body)

    def _parse_call_effect(self) -> CallEffect:
        self.expect_kw("call")
        name = self.expect_ident()
        self.expect_sym("(")
        args: list[Expr] = []
        if not (self.peek().kind == "sym" and self.peek().value == ")"):
            while True:
                args.append(self.parse_expr())
                if self.accept_sym(","):
                    continue
                break
        self.expect_sym(")")
        return CallEffect(name, tuple(args))

    def _parse_guard(self) -> Guard:
        self.expect_kw("guard")
        return Guard(self.parse_expr())

    def _parse_return(self) -> Return:
        self.expect_kw("return")
        if self.peek().kind == "sym" and self.peek().value in (";", "}", "od", "<EOF>", ","):
            return Return(None)
        return Return(self.parse_expr())

    def _parse_simple(self) -> EffectExpr:
        # Assignment: IDENT ' = expr   |  SetUpdate: IDENT ' = ( IDENT \ {expr}) ∪ {expr}
        if self.peek().kind == "ident" and self.peek(1).kind == "sym" and self.peek(1).value == "'":
            name = self.advance().value
            self.expect_sym("'")
            self.expect_sym("=")
            if self.peek().kind == "sym" and self.peek().value == "(":
                # lookahead: ( IDENT \ { ... }
                save = self.i
                self.advance()  # (
                if self.peek().kind == "ident" and self.peek(1).kind == "sym" and self.peek(1).value == "\\":
                    src = self.advance().value
                    self.advance()  # \
                    self.expect_sym("{")
                    removed = self.parse_expr()
                    self.expect_sym("}")
                    self.expect_sym(")")
                    self.expect_sym("∪")
                    self.expect_sym("{")
                    added = self.parse_expr()
                    self.expect_sym("}")
                    return SetUpdate(name, src, removed, added)
                self.i = save
            return Assign(name, self.parse_expr())
        return ExprStmt(self.parse_expr())


def parse_effect(text: str) -> EffectExpr:
    """Parse an EffectExpr string into its frozen AST."""
    p = _Parser(text)
    effect = p.parse_effect()
    if p.peek().kind != "sym" or p.peek().value != "<EOF>":
        # allow a trailing `;` or newline in the input before EOF
        if not (p.peek().kind == "sym" and p.peek().value in ("<EOF>", ";")):
            raise ValueError(f"trailing tokens at position {p.peek().pos}: {p.peek().value!r}")
    return effect
