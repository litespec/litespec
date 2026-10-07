"""Comprehensive Rust-lowering tests: all compound effect constructors."""

from litespec.lir.parser import parse_effect
from litespec.lowering import render_effect_rust


def test_render_conditional():
    e = parse_effect("if x < 10 then y' = 1 else y' = 2")
    rust = render_effect_rust(e, {"y": "Nat"})
    assert "if x < 10 {" in rust
    assert "} else {" in rust


def test_render_for_range():
    e = parse_effect("for x : Nat in xs do x' = x od")
    rust = render_effect_rust(e, {"x": "Nat"})
    assert "for x in xs {" in rust


def test_render_do_while():
    e = parse_effect("do x' = 1 while x < 5 od")
    rust = render_effect_rust(e, {"x": "Nat"})
    assert "loop {" in rust
    assert "break;" in rust


def test_render_guard():
    e = parse_effect("guard x < 10")
    rust = render_effect_rust(e, {"x": "Nat"})
    assert "assert!" in rust


def test_render_return_no_arg():
    rust = render_effect_rust(parse_effect("return"), {})
    assert "return;" in rust


def test_render_call_effect():
    e = parse_effect("call foo(1)")
    rust = render_effect_rust(e, {})
    assert "foo(1);" in rust


def test_render_sequence_declares_once():
    e = parse_effect("seq { x' = 1; x' = x + 1 }")
    rust = render_effect_rust(e, {"x": "Nat"})
    assert rust.count("let mut x") == 1  # declared once, then reassigned
    assert "x = (x).wrapping_add(1);" in rust
