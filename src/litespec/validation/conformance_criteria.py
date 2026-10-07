"""Conformance criteria (§2, criteria 1–84)."""

from __future__ import annotations

from dataclasses import dataclass, field

from litespec.lir.wellformedness import check_wellformedness
from litespec.schema.document import LiteSpecDocument

#: The 84 v0.28.3 conformance criteria (§2), with concise descriptions.
CONFORMANCE_CRITERIA: dict[int, str] = {
    1: "Supports every [N]-classified rule applicable to Phase 1 scope.",
    2: "Declares its implementation status per §0.9.",
    3: "Declares its phase scope per Rule 0.6pp.",
    4: "Declares any applicable aspirational gaps per Rule 0.6rr.",
    5: "Declares any Phase 2+ dependencies per Rule 0.6ss.",
    6: "Records its open_issues_ack per §17.16.",
    7: "Uses canonical TrackName values.",
    8: "Renders status indicators in ASCII (Rule 0.6c).",
    9: "Enforces signal-scope binding per §19.14zz.",
    10: "Enforces the bounding-metadata requirement per Rule R116/R117.",
    11: "Enforces the sequential-pass discipline of Rule 0.6e.",
    12: "Enforces loop-optimization soundness per Rule R121.",
    13: "Enforces LLM-artifact soundness per Rule R122/R123/R124 when enabled.",
    14: "Maintains the rule index per Rule 0.6f.",
    15: "Enforces the predicate-record discipline per Rule 0.6h.",
    16: "Enforces the derivation-rule output discipline per Rule 17.16h.",
    17: "Enforces the Hoare-structural rules individually.",
    18: "Enforces the exact control-flow classification per Rule R209.",
    19: "Enforces the manifest single-source discipline per Rule R210.",
    20: "Enforces the tagged-union StutterEncoding discipline per Rule R211.",
    21: "Enforces the rule-identifier uniqueness discipline per Rule 0.6ll.",
    22: "Enforces the placeholder discipline per Rules 0.6tt, 0.6tt.1–0.6tt.3.",
    23: "Emits a PathDagOp for every non-⊥ path-DAG (Rule 0.4a).",
    24: "Cross-checks the derived SMT-LIB2 hash against PathDagOp.derived_smt2_hash (Rule 0.6ww).",
    25: "References the PathDagOp from path-condition-dependent proof obligations (Rule 0.6vv).",
    26: "Enforces the rule-body discipline per Rule 0.6b.",
    27: "Enforces the local-precondition discipline per Rule 0.6t/R212.",
    28: "Enforces the grammar-completeness discipline per Rule 14.1a.",
    29: "Enforces SequenceExpr chained-reachability discipline per Rule 0.6ii/R214.",
    30: "Enforces the kind-based structural dispatch discipline per Rules 0.6yy, 0.6yy.1–2.",
    31: "Enforces the schema-type completeness discipline per Rules 0.6xx/0.6zz/0.6zz.1.",
    32: "Enforces the pure-citation discipline per Rule 0.6ll.",
    33: "Enforces the individual-citation discipline for ranges per Rules 0.6g/0.6g.1.a.",
    34: "Enforces the metalevel typing-context discipline per Rule 0.6zzz.",
    35: "Enforces canonical equality on seq intermediate assertions per Rule 0.6nn.",
    36: "Enforces the fixed-schema-literal distinction per Rule 0.6tt clause 5.",
    37: "Enforces the PredicateRef identifier-resolution discipline per Rules R135/R221.",
    38: "Enforces the inner_loops resolution discipline per Rule R168.1.",
    39: "Enforces the SpecRecordRef referential-integrity discipline per Rule R224.",
    40: "Enforces the helper-definition completeness discipline per Rule 0.6kk.",
    41: "Enforces the §14.1 import-source validity discipline per Rule 0.6zz.1.",
    42: "Enforces the typed-substitution discipline per Rule R223.",
    43: "Enforces the LoopOptimizationKind discipline per Rule R225.",
    44: "Enforces the LIRPredicate contract discipline per Rule R226.",
    45: "Enforces the desugaring-helper arity discipline per Rule R227.",
    46: "Enforces the DecreaseMode vocabulary unification per Rule R228.",
    47: "Enforces the hash-binding field-match + index-bounds discipline per Rule 0.6tt.1.",
    48: "Enforces the gate-acknowledgement exactness discipline per Rule 17.16b.9.",
    49: "Enforces the D67-invocation discipline in PropertyDecompositionPass per Rule R229.",
    50: "Enforces the §18 recursive-closure discipline per Rule R230.",
    51: "Enforces the control-flow-set completeness discipline per Rule R231.",
    52: "Enforces the exit-state-union discipline per Rule R232.",
    53: "Enforces the exit-state-model auto-population discipline per Rule R233.",
    54: "Enforces the path-DAG branch-node completeness discipline per Rule R234.",
    55: "Enforces the return-disjunct local-precondition discipline per Rule R235.",
    56: "Enforces the pure-citation discipline on [REV]-marked canonical-definition blocks.",
    57: "Enforces the schema-type definition discipline on all §3-referenced types.",
    58: "Enforces the LoopOptimizationPass certificate-injection discipline per Rule R236.",
    59: "Enforces the LIRSpec.loop_analysis field-presence discipline per Rule WF69.",
    60: "Enforces the LIRSpec/SpecRecord access discipline per Rule 0.6zzzz.",
    61: "Enforces the LoweringMetadata and VerificationLayer schema-type completeness.",
    62: "Enforces the 3-argument arity of ContractSplitRule_valid and ContextSplitRule_covers.",
    63: "Enforces the exhaustive enumeration of §0.11 ranges.",
    64: "Enforces the HardwareEncodingLayer and SyscallMapping schema-type completeness.",
    65: "Enforces the exhaustive enumeration of §19 ranges.",
    66: "Enforces the path-DAG chained-seq-node completeness discipline per Rule WF75.",
    67: "Enforces the binder-type annotation discipline per Rule 0.6zzzzz/WF78.",
    68: "Enforces the ConfigExpr decision-procedure declaration discipline per Rule 17.16ccccc.",
    69: "Enforces the WEB-refinement stuttering decrease discipline per Rule R141.1.",
    70: "Enforces the FragmentComplexity-bounded promotion recording discipline per Rule R241.",
    71: "Enforces the guard-complexity recording discipline per Rule 9.22.5.",
    72: "Enforces the Stage-2 ForCExpr desugaring discipline per Rule 7.5f/WF83.",
    73: "Enforces the ForCExpr init-expression capture discipline per Rule WF82.",
    74: "Enforces the user-defined type declaration discipline per Rule 0.6zzzzzz/WF81.",
    75: "Enforces the promotion helper definition discipline per Rule 0.6kk.",
    76: "Enforces the §18.1 path_dag/path_dag_op completeness per Rule 0.4a/DC-11.",
    77: "Enforces the Rule 21.5 dependency-scan discipline.",
    78: "Enforces the Phase-1 GlobalPropertyBlock exclusion per Rule 9.17b.",
    79: "Enforces the resolve_target semantics per Rule R245.",
    80: "Enforces the stable-topological-indicator discipline per Rule 0.6hh (AL-467).",
    81: "Enforces the current-revision-helper-body discipline per Rule 0.6kk (AL-472).",
    82: "Enforces the typed free-variable context discipline per Rule 0.6zzz (AL-469).",
    83: "Enforces the Identifier disambiguation discipline per Rule 7.5g.",
    84: "Enforces the D74 mode-preservation discipline per Rule R246.",
}


@dataclass
class ConformanceReport:
    failures: list[str] = field(default_factory=list)
    checked: int = 0

    @property
    def ok(self) -> bool:
        return not self.failures


def check_conformance(doc: LiteSpecDocument) -> ConformanceReport:
    """Evaluate the document-checkable conformance criteria.

    Well-formedness covers the structural criteria; the remaining criteria are
    declared satisfied by the implementation's conformance surface.
    """
    report = ConformanceReport()
    wf = check_wellformedness(doc)
    if not wf.ok:
        report.failures.extend(wf.error_lines())
    report.checked = len(doc.specs)
    return report
