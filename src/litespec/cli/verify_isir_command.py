"""``verify-isir``: emit ISIR → InterScope property verification (Phase 7, post-α).

This is **not** equivalence checking. After the LIR→ISIR transition-system
abstraction, InterScope verifies generic *properties* (safety/invariants) carried
by the emitted proof obligations. Given a ``.c`` file (and optional function) it
emits a ``.isir`` module and hands it to InterScope's ``run.sh --verify``; given a
``.isir`` file it verifies directly. ``--backend structural`` runs LiteSpec's
EC-side α-coherence check (no InterScope toolchain needed).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from litespec.extraction import attach_contract, extract_function, parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.type_modeling import c_param_to_type_expr
from litespec.interscope.client import interscope_available, run_interscope
from litespec.interscope.isir import dumps_isir, emit_isir_module, validate_isir


def _emit(source: bytes, name: str, backend: str = "acl2") -> str:
    fn = extract_function(source, name)
    contract = attach_contract(source, name)
    if not contract.postconditions and not contract.preconditions:
        from litespec.extraction.contract_attachment import synthesize_contract

        contract = synthesize_contract(fn.return_type, name)
    params = [(n, c_param_to_type_expr(t, n)) for n, t in fn.parameters]
    isir = emit_isir_module(name, fn.state_vars, fn.effect, contract, params=params, backend=backend)
    check = validate_isir(isir)
    if not check.ok:
        raise SystemExit(f"verify-isir: invalid ISIR for {name}: {check.errors}")
    return dumps_isir(isir)


def verify_isir_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="litespec verify-isir", description="Emit ISIR → InterScope backend verification"
    )
    parser.add_argument("file", help="path to a .c source file or a .isir file")
    parser.add_argument("--function", "-f", dest="function", help="function to verify (for .c input)")
    parser.add_argument(
        "--backend",
        default=None,
        help="InterScope backend name (e.g. symbiyosys), or 'structural' for the in-repo backend",
    )
    args = parser.parse_args(argv)

    # The in-repo structural backend needs no InterScope toolchain.
    if args.backend == "structural":
        from litespec.interscope.backends import discharge

        path = Path(args.file)
        if path.suffix != ".isir":
            source = path.read_bytes()
            fns = [f.name for f in functions(parse_c(source)) if f.name]
            name = args.function or (fns[0] if len(fns) == 1 else None)
            if name is None:
                print("verify-isir: pass --function to select one function", file=sys.stderr)
                return 1
            isir_text = _emit(source, name)
            import yaml

            isir = yaml.safe_load(isir_text)
        else:
            import yaml

            isir = yaml.safe_load(path.read_text(encoding="utf-8"))
        result = discharge(isir)
        print(f"verify-isir [{args.backend}]: {result.status.upper()}")
        for r in result.reports:
            print(f"      {r}")
        for e in result.errors:
            print(f"      error: {e}")
        return 0 if result.status == "pass" else 1

    if not interscope_available():
        print("verify-isir: InterScope not installed (run ./install.sh --interscope-only)", file=sys.stderr)
        print("verify-isir: use --backend structural for the in-repo backend", file=sys.stderr)
        return 2

    path = Path(args.file)
    if path.suffix == ".isir":
        # Resolve to an absolute path: run_interscope executes with cwd=the
        # InterScope clone, so a relative path would resolve against the clone.
        isir_file = path.resolve()
    else:
        source = path.read_bytes()
        fns = [f.name for f in functions(parse_c(source)) if f.name]
        if args.function:
            if args.function not in fns:
                print(f"verify-isir: function {args.function!r} not found", file=sys.stderr)
                return 1
            fns = [args.function]
        elif len(fns) != 1:
            print(f"verify-isir: {len(fns)} functions found; pass --function to select one", file=sys.stderr)
            return 1
        name = fns[0]
        backend = args.backend or "acl2"
        with tempfile.NamedTemporaryFile("w", suffix=".isir", delete=False) as tmp:
            tmp.write(_emit(source, name, backend=backend))
            isir_file = Path(tmp.name)

    cmd = ["--verify", str(isir_file)]
    if args.backend:
        cmd += ["--backend", args.backend]
    result = run_interscope(cmd)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return 0 if result.ok else 1
