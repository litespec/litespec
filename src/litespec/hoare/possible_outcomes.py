"""Possible-outcome computation (§9.21.3 ``possible_outcomes`` family)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.decomposition_block import SubPart
from litespec.schema.exit_state import ExitState
from litespec.schema.hoare_triple import HoareTriple

SubPartLookup = dict[str, Optional[SubPart]]


def exit_kinds(es: Optional[ExitState]) -> set[str]:
    if es is None:
        return set()
    return {kind_of_disjunct(d) for d in es.disjuncts}


def kind_of_disjunct(d) -> str:
    return {"return": "returning", "break": "breaking", "continue": "continuing"}.get(
        str(d.target_kind), str(d.target_kind)
    )


def exit_kinds_of_subpart(sp: SubPart) -> set[str]:
    return exit_kinds(sp.hoare_triple.exit_state) if sp.hoare_triple is not None else set()


def possible_outcomes_of_subpart(sp: SubPart, lookup: SubPartLookup) -> set[str]:
    """Exact control-flow outcomes of a sub-part."""
    t: Optional[HoareTriple] = sp.hoare_triple
    if t is None:
        return {"normal"}
    rule = str(t.rule.rule)
    if rule == "return":
        return {"returning"}
    if rule == "seq":
        segs = [lookup.get(r.sub_part) for r in t.rule.premise_refs]
        segs = [s for s in segs if s is not None]
        return possible_outcomes_of_seq(segs, lookup) | (exit_kinds(t.exit_state) - {"normal"})
    if rule == "if":
        then = _branch(lookup, t, "if_then_branch")
        els = _branch(lookup, t, "if_else_branch")
        out = set()
        for b in (then, els):
            if b is not None:
                out |= possible_outcomes_of_subpart(b, lookup)
        return out or {"normal"}
    if rule == "while":
        return {"normal"} | (exit_kinds(t.exit_state) - {"normal"})
    if rule in ("let", "quant_forall", "quant_exists_finite"):
        inner = _inner_body(lookup, sp)
        return possible_outcomes_of_subpart(inner, lookup) if inner is not None else {"normal"}
    return (exit_kinds(t.exit_state) - {"normal"}) | {"normal"}


def possible_outcomes_of_seq(segs: list[SubPart], lookup: SubPartLookup) -> set[str]:
    if not segs:
        return {"normal"}
    head = possible_outcomes_of_subpart(segs[0], lookup)
    if "normal" in head:
        return (head - {"normal"}) | possible_outcomes_of_seq(segs[1:], lookup)
    return head


def _branch(lookup: SubPartLookup, t: HoareTriple, kind: str) -> Optional[SubPart]:
    for r in t.rule.premise_refs:
        sp = lookup.get(r.sub_part)
        if sp is not None and str(sp.kind) == kind:
            return sp
    return None


def _inner_body(lookup: SubPartLookup, sp: SubPart) -> Optional[SubPart]:
    t = sp.hoare_triple
    if t is None:
        return None
    for r in t.rule.premise_refs:
        inner = lookup.get(r.sub_part)
        if inner is not None:
            return inner
    return None
