"""In-repo α-coherence check for the LIR→ISIR abstraction seam (Phase 8, EC-side).

This is **not** an InterScope backend and is **not** for EC discharge via
InterScope. InterScope verifies generic *properties* on the abstracted transition
system (see ``verify-isir``) — a separate, post-abstraction stage. This module is
LiteSpec's own EC-side check that the α relation is derived and coherent (total,
type-coherent, observably preserving) against the emitted transition system.
"""

from __future__ import annotations

from litespec.pipeline.pipeline_state import CheckResult

BACKEND_NAME = "structural"


def _state_vars(module: dict) -> list[tuple[str, str]]:
    return [(s.get("name", ""), s.get("type", "Nat")) for s in module.get("state", [])]


def discharge(isir: dict) -> CheckResult:
    """Structurally confirm the abstraction for an ISIR module dict."""
    errors: list[str] = []
    reports: list[str] = []

    module = isir.get("module")
    if not isinstance(module, dict):
        return CheckResult(status="fail", errors=["structural backend: ISIR has no module"])

    abstraction = module.get("abstraction") or {}
    relation = abstraction.get("relation") or {}
    signals = abstraction.get("signals", [])
    state = _state_vars(module)
    rules = module.get("rules", [])

    # 1. the α-relation must be emitted with a map expression.
    map_expr = relation.get("map_expr", "")
    if not relation or not map_expr:
        errors.append("structural backend: abstraction relation α (map_expr) not emitted")

    # 2. totality / type-coherence / observable-preservation (Rules R91 / 9.15a).
    from litespec.abstraction import observable_preservation_check, totality_check, type_coherence_check

    for check, label in (
        (totality_check, "total"),
        (type_coherence_check, "type-coherent"),
        (observable_preservation_check, "observably preserving"),
    ):
        ok, msg = check(state, signals)
        if ok:
            reports.append(f"α {label} ✓")
        else:
            errors.append(f"α not {label}: {msg}")

    # 3. the refinement target must reference a real transition (a rule).
    if not rules:
        if state:
            errors.append("structural backend: module has no rules (no transition system to refine)")
        else:
            reports.append("structural backend: pure function (no state → trivial α, no transition rules)")
    else:
        for rule in rules:
            if not rule.get("name"):
                errors.append("structural backend: rule missing name")
            if "action" not in rule:
                errors.append(f"structural backend: rule {rule.get('name', '?')!r} missing action")

    # 4. totality flag on the relation record must be true (Rule 9.15a).
    if relation.get("totality") is not True:
        errors.append("structural backend: relation.totality is not true")

    if errors:
        return CheckResult(status="fail", errors=errors, reports=reports)
    reports.insert(0, f"structural backend: α = {map_expr}")
    reports.append(f"structural backend: {len(rules)} rule(s) refine {len(state)} state variable(s)")
    return CheckResult(status="pass", reports=reports)
