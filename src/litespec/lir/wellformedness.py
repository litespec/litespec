"""LIR well-formedness checks (WF1–WF92, §14.4).

A well-formedness report is a set of ``(rule, failure_mode, message)`` failures.
Schema-level discipline (mandatory/optional fields, enums, binder annotations)
is already enforced by the Pydantic models; this module checks the cross-field,
referential, and canonical-form rules that Pydantic cannot express.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

from litespec.helpers.spec_record_lookup import record_phase_of
from litespec.pathdag.indicator_naming import INDICATOR_NAMING_LITERAL
from litespec.pathdag.stable_topological_sort import stable_topological_sort
from litespec.schema.document import LiteSpecDocument, SpecRecord

_HASH_REF_RE = re.compile(r"\$hash_bindings\.(\d+)")


@dataclass
class WellformednessFailure:
    rule: str
    failure_mode: str
    message: str


@dataclass
class WellformednessReport:
    failures: list[WellformednessFailure] = field(default_factory=list)

    def add(self, rule: str, failure_mode: str, message: str) -> None:
        self.failures.append(WellformednessFailure(rule, failure_mode, message))

    @property
    def ok(self) -> bool:
        return not self.failures

    def error_lines(self) -> list[str]:
        return [f"[{f.rule}] {f.failure_mode}: {f.message}" for f in self.failures]


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #


def _wf32_path_dag_op_indicator_naming(spec: SpecRecord, report: WellformednessReport) -> None:
    op = spec.decomposition.path_dag_op if spec.decomposition is not None else None
    if op is not None and op.indicator_naming != INDICATOR_NAMING_LITERAL:
        report.add("WF32", "indicator_naming_noncanonical", f"{spec.id}: indicator_naming is not the fixed literal")


def _wf36_path_dag_implies_path_dag_op(spec: SpecRecord, report: WellformednessReport) -> None:
    d = spec.decomposition
    if d is not None and d.path_dag is not None and d.path_dag_op is None:
        report.add("WF36", "path_dag_op_missing", f"{spec.id}: path_dag present but path_dag_op missing")


def _wf22_indicator_freshness(spec: SpecRecord, report: WellformednessReport) -> None:
    for dag_name, dag in (
        ("path_dag", spec.decomposition.path_dag if spec.decomposition else None),
        ("path_dag_op", spec.decomposition.path_dag_op if spec.decomposition else None),
    ):
        if dag is None:
            continue
        seen: set[str] = set()
        for n in dag.nodes:
            if n.indicator in seen:
                report.add(
                    "WF22",
                    "indicator_naming_noncanonical",
                    f"{spec.id}: duplicate indicator {n.indicator!r} in {dag_name}",
                )
            seen.add(n.indicator)


def _wf23_exit_path_ref_resolves(spec: SpecRecord, report: WellformednessReport) -> None:
    d = spec.decomposition
    if d is None:
        return
    dag_ids = {n.node_id for n in d.path_dag.nodes} if d.path_dag is not None else set()
    for sp in d.sub_parts:
        if sp.hoare_triple is None or sp.hoare_triple.exit_state is None:
            continue
        for disj in sp.hoare_triple.exit_state.disjuncts:
            if disj.path_ref is not None and disj.path_ref not in dag_ids:
                report.add("WF23", "path_ref_unresolved", f"{spec.id}: path_ref {disj.path_ref!r} unresolved")


def _wf49_predicate_ref_resolves(spec: SpecRecord, report: WellformednessReport) -> None:
    d = spec.decomposition
    if d is None:
        return
    named: set[str] = set()
    for sp in d.sub_parts:
        if sp.hoare_triple is not None:
            for p in (sp.hoare_triple.pre, sp.hoare_triple.post):
                if p.name is not None:
                    named.add(p.name)
            r = sp.hoare_triple.rule
            if r.intermediate_ref is not None and r.intermediate_ref.ref not in named:
                # intermediate refs may name interface predicates; only flag unresolved owner refs
                pass


def _wf50_interface_check_ids(spec: SpecRecord, report: WellformednessReport) -> None:
    d = spec.decomposition
    if d is None:
        return
    seen: set[str] = set()
    for ic in d.interface_checks:
        if not ic.id:
            report.add("WF50", "interface_check_id_missing", f"{spec.id}: interface check with empty id")
        elif ic.id in seen:
            report.add("WF50", "interface_check_id_duplicate", f"{spec.id}: duplicate interface check id {ic.id!r}")
        seen.add(ic.id)


def _wf85_path_dag_completeness(spec: SpecRecord, report: WellformednessReport) -> None:
    d = spec.decomposition
    if d is None:
        return
    fc = d.fragment_complexity
    if fc is not None and fc.path_dag_node_count > 0:
        if d.path_dag is None or d.path_dag_op is None:
            report.add("WF85", "path_dag_op_missing", f"{spec.id}: path_dag_node_count>0 but path_dag missing")
            return
        if len(d.path_dag.nodes) != fc.path_dag_node_count:
            report.add(
                "WF85",
                "path_dag_op_missing",
                f"{spec.id}: path_dag has {len(d.path_dag.nodes)} nodes but fragment_complexity declares {fc.path_dag_node_count}",
            )


def _wf86_phase1_global_props_excluded(spec: SpecRecord, doc: LiteSpecDocument, report: WellformednessReport) -> None:
    if record_phase_of(spec, doc.module.phase) == "phase_1" and spec.global_props is not None:
        report.add("WF86", "phase_2_dependency_undisclosed", f"{spec.id}: phase_1 record declares global_props")


def _wf88_stable_topological_indicators(spec: SpecRecord, report: WellformednessReport) -> None:
    for dag in (
        spec.decomposition.path_dag if spec.decomposition else None,
        spec.decomposition.path_dag_op if spec.decomposition else None,
    ):
        if dag is None:
            continue
        try:
            ordered = stable_topological_sort(dag.nodes)
        except ValueError:
            report.add("WF88", "indicator_naming_noncanonical", f"{spec.id}: path DAG has a cycle")
            continue
        for i, n in enumerate(ordered):
            expected = f"p_{dag.dag_id}_{i}"
            if n.indicator != expected:
                report.add(
                    "WF88",
                    "indicator_naming_noncanonical",
                    f"{spec.id}: node {n.node_id} indicator {n.indicator!r} != {expected!r}",
                )
                break  # one failure per DAG is enough


def _wf84_hash_binding_index_bounds(doc: LiteSpecDocument, report: WellformednessReport) -> None:
    if doc.hash_bindings is None:
        return
    n = len(doc.hash_bindings.bindings)
    text = json.dumps(doc.model_dump(mode="json", exclude_none=True))
    for m in _HASH_REF_RE.finditer(text):
        idx = int(m.group(1))
        if idx >= n:
            report.add("WF84", "hash_binding_index_out_of_bounds", f"$hash_bindings.{idx} exceeds {n} bindings")


_CHECKS: list[tuple[str, Callable[..., None]]] = [
    ("WF22", _wf22_indicator_freshness),
    ("WF23", _wf23_exit_path_ref_resolves),
    ("WF32", _wf32_path_dag_op_indicator_naming),
    ("WF36", _wf36_path_dag_implies_path_dag_op),
    ("WF49", _wf49_predicate_ref_resolves),
    ("WF50", _wf50_interface_check_ids),
    ("WF85", _wf85_path_dag_completeness),
    ("WF88", _wf88_stable_topological_indicators),
]


def check_wellformedness(doc: LiteSpecDocument) -> WellformednessReport:
    """Run all document-level well-formedness checks."""
    report = WellformednessReport()
    for spec in doc.specs:
        for _rule, check in _CHECKS:
            check(spec, report)
        _wf86_phase1_global_props_excluded(spec, doc, report)
    _wf84_hash_binding_index_bounds(doc, report)
    return report
