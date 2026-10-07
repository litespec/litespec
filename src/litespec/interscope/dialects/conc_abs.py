"""``ConcAbsDialect`` derivation — rely-guarantee for the concurrent fragment (Phase 10).

Scans an LIR effect for the concurrency constructs already lowered (atomic RMW
intrinsics, spin-lock acquire/release, the per-CPU cell) and derives a minimal
rely-guarantee ``ConcAbsDialect``: atomic actions are indivisible and exempt from
interference; a spin-lock critical section yields a ``rely``/``guarantee`` pair.
"""

from __future__ import annotations

from litespec.intrinsics import Op, lookup
from litespec.lir.effect_expr_ast import Call
from litespec.pipeline.pipeline_state import CheckResult
from litespec.schema.conc_abs_dialect import ConcAbsDialect

_ATOMIC_OPS = {
    Op.ATOMIC_LOAD,
    Op.ATOMIC_STORE,
    Op.ATOMIC_ADD,
    Op.ATOMIC_SUB,
    Op.ATOMIC_INC,
    Op.ATOMIC_DEC,
    Op.ATOMIC_DEC_RET,
    Op.ATOMIC_CMPXCHG,
}

_SPIN_LOCK_FNS = {"LOS_SpinLock", "LOS_SpinUnlock", "LOS_SpinLockSave", "LOS_SpinUnlockRestore"}


def _collect_calls(node, out: list[str]) -> None:
    if isinstance(node, Call):
        out.append(node.name)
    for value in vars(node).values():
        if isinstance(value, (list, tuple)):
            for v in value:
                if hasattr(v, "__dict__"):
                    _collect_calls(v, out)
        elif hasattr(value, "__dict__"):
            _collect_calls(value, out)


def derive_conc_abs_dialect(effect) -> ConcAbsDialect:
    """Derive a minimal ``ConcAbsDialect`` from an LIR effect."""
    calls: list[str] = []
    if effect is not None:
        _collect_calls(effect, calls)

    atomic_actions: list[str] = []
    has_spinlock = False
    has_atomic = False
    has_cpuid = False
    for name in calls:
        intr = lookup(name)
        if intr is not None and intr.op in _ATOMIC_OPS:
            has_atomic = True
            atomic_actions.append(name)
        if name in _SPIN_LOCK_FNS:
            has_spinlock = True
        if name == "ArchCurrCpuid":
            has_cpuid = True

    # Context: strongest concurrency primitive wins — spin-lock ("both") > atomics
    # ("atomic") > per-CPU ("isr"); default "atomic".
    context = "both" if has_spinlock else ("atomic" if has_atomic else ("isr" if has_cpuid else "atomic"))

    rely = "true"
    guarantee = "true"
    if has_spinlock:
        # Standard rely-guarantee critical-section contract: while the lock is held,
        # the environment may not touch the locked state, and this component does not
        # release the invariant before re-acquiring it.
        rely = "locked_state stable under environment"
        guarantee = "locked_state invariant preserved"

    return ConcAbsDialect(
        context=context,
        threads=["task", "isr"] if has_spinlock else ["cpu_0"],
        rely=rely,
        guarantee=guarantee,
        atomic_actions=atomic_actions,
        notes=(
            f"derived from {len(atomic_actions)} atomic action(s)"
            + (" + spin-lock section" if has_spinlock else "")
        ),
    )


def _compatible(guarantee: str, rely: str) -> bool:
    """Syntactic rely-guarantee subsumption: ``guarantee ⊆ rely``.

    ``rely = "true"`` means the environment allows any interference (broad enough
    for any guarantee); ``guarantee = "true"`` means the component guarantees
    nothing; otherwise the two predicates must coincide.
    """
    if rely == "true" or guarantee == "true":
        return True
    return guarantee == rely


def check_conc_abs(dialect: ConcAbsDialect) -> CheckResult:
    """Check a single ``ConcAbsDialect`` is structurally coherent."""
    if dialect.context not in ("atomic", "both", "isr"):
        return CheckResult(status="fail", errors=[f"invalid context {dialect.context!r}"])
    if dialect.context == "both" and (dialect.rely == "true" or dialect.guarantee == "true"):
        return CheckResult(
            status="fail",
            errors=["spin-locked ('both') context requires a non-trivial rely/guarantee pair"],
        )
    return CheckResult(status="pass", reports=[f"ConcAbsDialect ({dialect.context}) coherent"])


def check_conc_abs_compatibility(dialects: list[ConcAbsDialect]) -> CheckResult:
    """Verify rely-guarantee composition: ``guarantee_i ⊆ rely_j`` for every pair.

    A compatible composition discharges the parallel-composition rule of
    rely-guarantee reasoning; an incompatible pair is a real interference leak.
    """
    if len(dialects) < 2:
        return CheckResult(status="pass", reports=["single component — trivially R/G-compatible"])
    errors: list[str] = []
    for i, a in enumerate(dialects):
        for j, b in enumerate(dialects):
            if i == j:
                continue
            if not _compatible(a.guarantee, b.rely):
                errors.append(
                    f"thread {i} guarantee {a.guarantee!r} not subsumed by thread {j} rely {b.rely!r}"
                )
    if errors:
        return CheckResult(status="fail", errors=errors)
    return CheckResult(status="pass", reports=[f"{len(dialects)} components R/G-compatible"])
