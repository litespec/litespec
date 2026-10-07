"""``emit-isir`` command: extract C → emit ``.isir`` files (Phase 7)."""

from __future__ import annotations

import argparse
import sys

from litespec.extraction import attach_contract, extract_function, parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.type_modeling import c_param_to_type_expr
from litespec.interscope.isir import dumps_isir, emit_isir_module, validate_isir
from litespec.targets import isir_output_dir, load_target, resolve_target


def emit_isir_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="litespec emit-isir", description="Emit .isir files from C")
    parser.add_argument("file", help="path to a .c file")
    parser.add_argument("function", nargs="?", help="function name (default: all)")
    parser.add_argument("--target", default=None, help="target requirements name (config/targets/<name>.yaml)")
    args = parser.parse_args(argv)

    target_cfg = load_target(resolve_target(args.target))
    out_base = isir_output_dir(target_cfg)

    with open(args.file, "rb") as fh:
        source = fh.read()

    fns = [f for f in functions(parse_c(source))]
    if args.function:
        fns = [f for f in fns if f.name == args.function]

    for cfn in fns:
        module = target_cfg.module_for_function(cfn.name) or "unassigned"
        out_dir = out_base / module
        out_dir.mkdir(parents=True, exist_ok=True)

        fn = extract_function(source, cfn.name)
        contract = attach_contract(source, cfn.name)
        if not contract.postconditions and not contract.preconditions:
            from litespec.extraction.contract_attachment import synthesize_contract

            contract = synthesize_contract(fn.return_type, cfn.name)
        params = [(n, c_param_to_type_expr(t, n)) for n, t in fn.parameters]
        isir = emit_isir_module(cfn.name, fn.state_vars, fn.effect, contract, params=params)
        check = validate_isir(isir)
        if not check.ok:
            print(f"{cfn.name}: invalid ISIR: {check.errors}", file=sys.stderr)
            return 1
        target_file = out_dir / f"{cfn.name}.isir"
        target_file.write_text(dumps_isir(isir), encoding="utf-8")
        print(f"emitted {target_file}")
    return 0
