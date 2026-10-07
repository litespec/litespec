"""InterScope client base wrapper (interscope.md §6.1)."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from litespec.interscope.config import interscope_entry_point, interscope_root

#: ``run.sh --<sub>`` → Python module/script invoked under ``PYTHONPATH=src``.
_SUBCOMMANDS = {
    "verify": "isir.cli.verify",
    "compile": "isir.cli.compile",
    "sim": "isir.cli.sim",
    "lift": "isir.cli.lift",
    "check": "isir.cli.check",
    "query": "isir.cli.query",
    "vcd-to-trace": "scripts/vcd_to_trace.py",
    "extract-mapping": "scripts/extract_mapping.py",
}


@dataclass
class InterScopeResult:
    stdout: str
    stderr: str
    exit_code: int

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


def _venv_python(root: Path) -> Path | None:
    py = root / ".venv" / "bin" / "python"
    return py if py.exists() else None


def run_interscope(args: list[str]) -> InterScopeResult:
    """Invoke an InterScope subcommand and capture its output.

    Prefer the clone's own ``.venv/bin/python`` directly (with ``PYTHONPATH=src``):
    the clone's ``run.sh`` uses ``uv run``, which walks *up* from
    ``third_party/interscope`` and binds to LiteSpec's ``.venv`` instead of the
    clone's, so the clone's deps (jsonschema, …) would be missing. Falls back to
    ``run.sh`` when the clone has no ``.venv``.
    """
    root = Path(interscope_root())
    sub = args[0].lstrip("-") if args else ""
    python = _venv_python(root)

    if python is not None and sub in _SUBCOMMANDS:
        module = _SUBCOMMANDS[sub]
        if module.endswith(".py"):
            cmd = [str(python), module, *args[1:]]
        else:
            cmd = [str(python), "-m", module, *args[1:]]
        # Add the opam switch bins (Kōika: coqc/dune/ocamlfind; default: Coq 9.1 /
        # rocq-mcp) to PATH so the Kōika and model_checking backends can find their
        # OCaml/Coq toolchain, not just the venv's Python.
        opam_root = Path(os.environ.get("OPAMROOT", Path.home() / ".opam"))
        koika_switch = os.environ.get("KOIKA_SWITCH_NAME", "coq-8.18-ocaml-4.14")
        opam_bins = [p for p in (opam_root / koika_switch / "bin", opam_root / "default" / "bin") if p.is_dir()]
        path_parts = [str(p) for p in opam_bins] + [str(python.parent), os.environ.get("PATH", "")]
        env = {
            **os.environ,
            "PYTHONPATH": str(root / "src"),
            "VIRTUAL_ENV": str(root / ".venv"),
            "PATH": os.pathsep.join(path_parts),
        }
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(root))
        return InterScopeResult(stdout=proc.stdout, stderr=proc.stderr, exit_code=proc.returncode)

    cmd = [interscope_entry_point(), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return InterScopeResult(stdout=proc.stdout, stderr=proc.stderr, exit_code=proc.returncode)


def interscope_available() -> bool:
    return Path(interscope_root()).exists() and Path(interscope_entry_point()).exists()
