"""``decompose`` command: emit the D67 Hoare decomposition for a record's action."""

from __future__ import annotations

import argparse
import sys

from litespec.derivation.for_c_desugaring import desugar_for_c_in
from litespec.hoare import derive_hoare_decomposition
from litespec.lir.parser import parse_effect
from litespec.serialization import load_litespec


def decompose_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="litespec decompose", description="Emit the D67 Hoare decomposition")
    parser.add_argument("file", help="path to a .litespec.yaml file")
    args = parser.parse_args(argv)

    doc = load_litespec(args.file)
    if not doc.specs:
        print("no specs", file=sys.stderr)
        return 1

    spec = doc.specs[0]
    if spec.state_machine is None or not spec.state_machine.actions:
        print(f"spec {spec.id} has no LIR actions", file=sys.stderr)
        return 1

    action = spec.state_machine.actions[0]
    effect = parse_effect(action.effect)
    desugared = desugar_for_c_in(effect)
    result = derive_hoare_decomposition(desugared, action.name)

    print(f"# D67 Hoare decomposition for {spec.id} (action: {action.name})")
    print(f"parent rule: {result.parent_triple.rule.rule}")
    print(f"correctness: {result.correctness}")
    print(f"sub_parts: {len(result.sub_parts)}  interface_checks: {len(result.interface_checks)}")
    print()
    for sp in result.sub_parts:
        t = sp.hoare_triple
        prem = ",".join(r.sub_part for r in t.rule.premise_refs)
        print(f"  {sp.name:48s} [{sp.kind}] rule={t.rule.rule} premises=[{prem}]")
    print()
    print("## interface_checks")
    for ic in result.interface_checks:
        ia = ic.intermediate_assertion.expression if ic.intermediate_assertion else "-"
        print(f"  {ic.id}  {ic.caller} -> {ic.callee}  ({ic.relation_kind})  intermediate={ia}")
    return 0
