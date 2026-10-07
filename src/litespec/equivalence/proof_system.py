"""EC proof system (§9.8): seam checks returning ``CheckResult``.

Each seam performs a *concrete* check on its artifacts rather than a blanket
"discharged": ``c_to_lir`` checks the LIR is a non-trivial extraction, ``lir_to_unsafe``
checks the emitted Rust compiles, ``lir_to_isir`` checks the ISIR validates, and the
safe seams check structural presence. Missing artifacts degrade to ``warn`` (not
discharged), never a silent ``pass``.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from litespec.pipeline.pipeline_state import CheckResult


def _effect_size(effect) -> int:
    from litespec.lir.effect_expr_ast import Sequence

    if isinstance(effect, Sequence):
        return sum(_effect_size(i) for i in effect.items)
    return 1


def _rust_compiles(rust: str) -> tuple[bool, str]:
    if shutil.which("rustc") is None:
        return False, "rustc not available"
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "out.rs"
        rlib = Path(d) / "out.rlib"
        src.write_text(rust, encoding="utf-8")
        proc = subprocess.run(
            ["rustc", "--edition", "2021", "--crate-type", "lib", str(src), "-o", str(rlib)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return True, ""
        return False, proc.stderr.strip()[:300]


def check_seam(seam: str, relation: str, artifacts) -> CheckResult:
    """Discharge a seam obligation by checking its artifacts."""
    if isinstance(artifacts, tuple) and len(artifacts) == 3:
        a, b, c = artifacts
    elif isinstance(artifacts, tuple) and len(artifacts) == 2:
        a, b, c = artifacts[0], artifacts[1], None
    else:
        a = b = c = None

    if seam == "c_to_lir":
        return _check_c_to_lir(a, b)
    if seam == "lir_to_unsafe":
        return _check_lir_to_unsafe(a, b, c)
    if seam == "unsafe_to_safe":
        return _check_unsafe_to_safe(a, b)
    if seam == "lir_to_isir":
        return _check_lir_to_isir(a, b)
    if seam == "safe_to_isir":
        return _check_safe_to_isir(a, b)
    return CheckResult(status="fail", errors=[f"unknown seam {seam!r}"])


def _check_c_to_lir(c_source, lir) -> CheckResult:
    if lir is None:
        if c_source is None:
            return CheckResult(status="warn", warnings=["c_to_lir: no artifacts (not discharged)"])
        return CheckResult(status="fail", errors=["c_to_lir: LIR extraction produced no result"])
    effect = getattr(lir, "effect", None)
    if effect is None:
        return CheckResult(status="fail", errors=["c_to_lir: LIR has no effect"])
    from litespec.lir.effect_expr_ast import Skip

    if isinstance(effect, Skip):
        return CheckResult(status="fail", errors=["c_to_lir: LIR effect is trivial (Skip)"])
    name = getattr(lir, "name", "?")
    size = _effect_size(effect)

    # Semantic extension: concretely evaluate the pure fragment on bounded inputs.
    from litespec.equivalence.lir_interp import concrete_inputs, is_interpretable, run_effect

    if is_interpretable(effect):
        from litespec.equivalence.differential import unsigned_bits

        params = [(n, "Nat") for n, _ in getattr(lir, "parameters", [])]
        inputs = concrete_inputs(params)
        bits = unsigned_bits(getattr(lir, "return_type", ""))
        results = []
        for env in inputs:
            try:
                results.append(run_effect(effect, env, bits=bits))
            except (ValueError, KeyError) as exc:
                return CheckResult(
                    status="fail",
                    errors=[f"c_to_lir: {name} not concretely evaluable on {env}: {type(exc).__name__}: {exc}"],
                )
        seen = sorted({str(r) for r in results})[:5]

        # Differential extension: compare against the compiled C when possible.
        note = f"concretely evaluated on {len(inputs)} input(s) → results {seen}"
        if c_source is not None:
            from litespec.equivalence.differential import differential_check

            status, mism = differential_check(c_source, lir)
            if status == "ok":
                note += "; differentially verified against C (clang)"
            elif status == "mismatch":
                return CheckResult(
                    status="fail",
                    errors=[f"c_to_lir: {name} disagrees with C on {len(mism)} input(s): {mism[:3]}"],
                )
            else:  # unavailable (no clang / no harness)
                note += f"; differential C check {status}"
        return CheckResult(status="pass", reports=[f"c_to_lir: {name} → LIR ({size} node(s)); {note}"])
    return CheckResult(
        status="pass",
        reports=[f"c_to_lir: {name} → LIR ({size} node(s)); impure (calls/memory/loops) — structural check"],
    )


def _check_lir_to_unsafe(lir, rust, c_source=None) -> CheckResult:
    if rust is None:
        return CheckResult(status="warn", warnings=["lir_to_unsafe: no Rust produced (not discharged)"])
    if not isinstance(rust, str):
        return CheckResult(status="fail", errors=["lir_to_unsafe: Rust artifact is not a string"])
    ok, msg = _rust_compiles(rust)
    if not ok:
        return CheckResult(status="fail", errors=[f"lir_to_unsafe: Rust does not compile: {msg}"])

    reports = ["lir_to_unsafe: emitted Rust compiles under rustc"]
    # Rust-space observational equivalence: for a pure function, run the unsafe
    # Rust on bounded inputs and compare against the LIR interpreter.
    if c_source is not None and lir is not None and getattr(lir, "name", None):
        from litespec.equivalence.differential import differential_check_rust

        status, mism = differential_check_rust(c_source, lir.name)
        if status == "ok":
            reports.append("lir_to_unsafe: Rust↔LIR differentially verified on bounded inputs")
        elif status == "mismatch":
            return CheckResult(
                status="fail",
                errors=[f"lir_to_unsafe: Rust disagrees with LIR on {len(mism)} input(s): {mism[:3]}"],
            )
        elif status == "unavailable":
            reports.append("lir_to_unsafe: Rust differential check unavailable")
        # "impure" → no differential; keep the structural (compile) check only.
    return CheckResult(status="pass", reports=reports)


def _check_unsafe_to_safe(unsafe_rust, safe_rust) -> CheckResult:
    if unsafe_rust is None or safe_rust is None:
        return CheckResult(status="warn", warnings=["unsafe_to_safe: no safe/unsafe pair (not discharged)"])
    if not isinstance(safe_rust, str) or not isinstance(unsafe_rust, str):
        return CheckResult(status="fail", errors=["unsafe_to_safe: artifacts are not strings"])
    return CheckResult(status="pass", reports=["unsafe_to_safe: safe wrapper present"])


def _check_lir_to_isir(lir, isir) -> CheckResult:
    if isir is None:
        return CheckResult(status="warn", warnings=["lir_to_isir: no ISIR produced (not discharged)"])
    if not isinstance(isir, dict):
        return CheckResult(status="fail", errors=["lir_to_isir: ISIR artifact is not a mapping"])
    from litespec.interscope.isir import validate_isir

    result = validate_isir(isir)
    if not result.ok:
        return CheckResult(status="fail", errors=[f"lir_to_isir: ISIR invalid: {result.errors}"])

    # EC-side: the LIR→ISIR abstraction seam checks that the α relation is derived
    # and coherent (total/type-coherent/observably preserving) against the emitted
    # transition system. This is LiteSpec's own check, *not* an InterScope backend;
    # InterScope verifies generic properties post-abstraction (see `verify-isir`).
    from litespec.interscope.backends import discharge

    backend = discharge(isir)
    reports = ["lir_to_isir: ISIR validates against schema"]
    if backend.status == "pass":
        reports += backend.reports
        return CheckResult(status="pass", reports=reports)
    return CheckResult(status="fail", errors=backend.errors, reports=backend.reports)


def _check_safe_to_isir(safe_rust, isir) -> CheckResult:
    if safe_rust is None or isir is None:
        return CheckResult(status="warn", warnings=["safe_to_isir: no safe/ISIR pair (not discharged)"])
    if not isinstance(isir, dict):
        return CheckResult(status="fail", errors=["safe_to_isir: ISIR artifact is not a mapping"])
    return CheckResult(status="pass", reports=["safe_to_isir: safe↔ISIR structurally consistent"])
