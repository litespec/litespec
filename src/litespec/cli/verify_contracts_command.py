"""``verify-contracts``: run a target's arch-neutral interface contracts.

Usage: ``litespec verify-contracts [--target <name>] [--source <combined.c>]``

With no ``--source`` the ``arch_mmu`` module is generated on the fly. Each declared
``interface.contracts`` entry is checked against the same observable contract; exit
status is non-zero if any contract fails.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from litespec.equivalence.contracts import verify_contracts
from litespec.targets.loader import load_target, resolve_target
from litespec.type_mapping import load_type_model


def _generate_combined(module: str) -> Path:
    root = Path(__file__).resolve().parents[3]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "generate_combined_sources.py"), module, "--out", "/tmp"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(f"failed to generate combined source for {module!r}")
    return Path(f"/tmp/los_{module}_combined.c")


def verify_contracts_command(argv: list[str]) -> int:
    target_name: str | None = None
    source_path: str | None = None
    i = 0
    while i < len(argv):
        if argv[i] in ("--target", "-t") and i + 1 < len(argv):
            target_name, i = argv[i + 1], i + 2
        elif argv[i] in ("--source", "-s") and i + 1 < len(argv):
            source_path, i = argv[i + 1], i + 2
        else:
            i += 1

    target_name = resolve_target(target_name)
    target = load_target(target_name)
    if not target.interface_contracts:
        print(f"litespec verify-contracts: target {target_name!r} declares no interface.contracts", file=sys.stderr)
        return 2

    src = Path(source_path) if source_path else _generate_combined("arch_mmu")
    c_source = src.read_bytes()
    tm = load_type_model(target.type_model)
    results = verify_contracts(c_source, target.interface_contracts, tm, target.memory_config)

    failed = False
    for r in results:
        print(f"[{r.status}] {r.fn}  (contract: {r.contract})")
        for line in r.reports:
            print(f"      {line}")
        if r.status != "pass":
            failed = True
    return 1 if failed else 0
