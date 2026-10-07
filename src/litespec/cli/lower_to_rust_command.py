"""``lower-to-rust`` command: extract C → LIR → emit Rust (Phase 4)."""

from __future__ import annotations

import argparse

from litespec.extraction import extract_function, parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.type_modeling import c_param_to_type_expr, c_return_to_type_expr
from litespec.lowering import emit_module


def lower_to_rust_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="litespec lower-to-rust", description="Extract C and emit Rust")
    parser.add_argument("file", help="path to a .c file")
    parser.add_argument("function", nargs="?", help="function name (default: all)")
    args = parser.parse_args(argv)

    with open(args.file, "rb") as fh:
        source = fh.read()

    fns = [f for f in functions(parse_c(source))]
    if args.function:
        fns = [f for f in fns if f.name == args.function]

    for cfn in fns:
        fn = extract_function(source, cfn.name)
        params = [(n, c_param_to_type_expr(t, n)) for n, t in fn.parameters]
        return_type = c_return_to_type_expr(fn.return_type)
        rust = emit_module(fn.name, params, return_type, fn.state_vars, fn.effect)
        print(f"// === {fn.name} ===")
        print(rust)
    return 0
