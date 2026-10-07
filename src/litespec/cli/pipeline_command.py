"""``pipeline`` command: full Stage 1→2→5 pipeline → ``PathDagOp`` + SMT-LIB2."""

from __future__ import annotations

import argparse
import sys

from litespec.hoare import derive_hoare_decomposition
from litespec.lir.parser import parse_effect
from litespec.pathdag import derive_smt2_form
from litespec.pipeline.lir_pipeline import fallthrough_from_decomposition, run_lir_pipeline
from litespec.serialization import load_litespec


def pipeline_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="litespec pipeline", description="Run the full pipeline end-to-end")
    parser.add_argument("file", help="path to a .litespec.yaml file")
    args = parser.parse_args(argv)

    doc = load_litespec(args.file)
    if not doc.specs:
        print("no specs", file=sys.stderr)
        return 1

    spec = doc.specs[0]
    action = spec.state_machine.actions[0]
    effect = parse_effect(action.effect)
    dag_id = f"{spec.id}_dag"

    # Stage 1→2: desugar; D67: Hoare decomposition.
    desugared, op = run_lir_pipeline(effect, dag_id, fallthrough=fallthrough_from_decomposition(spec))
    hoare = derive_hoare_decomposition(desugared, action.name)

    print(f"# Pipeline for {spec.id} (action: {action.name})")
    print(f"Hoare sub-parts: {len(hoare.sub_parts)}  (correctness={hoare.correctness})")
    print(f"PathDagOp: {op.dag_id}  root={op.root}  nodes={len(op.nodes)}")
    print(f"  indicator_naming: {op.indicator_naming}")
    print(f"  canonical_hash: {op.canonical_hash}")
    print(f"  derived_smt2_hash: {op.derived_smt2_hash}")
    print()
    for n in op.nodes:
        print(f"  {n.indicator}  [{n.kind}]  parent={n.parent}  guard={n.guard.expression}")
    print()
    print("## derived SMT-LIB2")
    print(derive_smt2_form(op).rstrip())
    return 0
