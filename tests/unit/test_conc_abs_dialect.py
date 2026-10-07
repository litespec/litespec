"""ConcAbsDialect derivation (concurrency — rely-guarantee)."""

from __future__ import annotations

from litespec.extraction import extract_function
from litespec.interscope.dialects import derive_conc_abs_dialect
from litespec.type_mapping import load_type_model


def test_derive_atomic_context():
    src = b"""
    typedef struct { volatile unsigned int counter; } Atomic;
    unsigned int smp_test(Atomic *v, unsigned int d) {
        unsigned int a = LOS_AtomicAdd(v, d);
        LOS_AtomicInc(v);
        return a;
    }
    """
    fn = extract_function(src, "smp_test", type_model=load_type_model("liteos"))
    d = derive_conc_abs_dialect(fn.effect)
    assert d.context == "atomic"
    assert "LOS_AtomicAdd" in d.atomic_actions
    assert "LOS_AtomicInc" in d.atomic_actions


def test_derive_spinlock_context():
    src = b"""
    typedef struct { volatile unsigned int lock; } Spin;
    unsigned int locked(Spin *s) {
        LOS_SpinLock(s);
        LOS_SpinUnlock(s);
        return 0;
    }
    """
    fn = extract_function(src, "locked", type_model=load_type_model("liteos"))
    d = derive_conc_abs_dialect(fn.effect)
    assert d.context == "both"
    assert d.threads == ["task", "isr"]
    assert d.rely != "true" and d.guarantee != "true"  # spin-lock R/G pair synthesized


def test_derive_default_context():
    src = b"unsigned int plain(unsigned int x) { return x + 1; }\n"
    fn = extract_function(src, "plain", type_model=load_type_model("liteos"))
    d = derive_conc_abs_dialect(fn.effect)
    assert d.context == "atomic"  # default
    assert d.atomic_actions == []


def test_conc_abstraction_emitted_only_for_concurrency():
    from litespec.interscope.isir import emit_isir_module

    tm = load_type_model("liteos")
    atomic_src = b"""
    typedef struct { volatile unsigned int counter; } Atomic;
    unsigned int smp_test(Atomic *v, unsigned int d) {
        unsigned int a = LOS_AtomicAdd(v, d);
        return a;
    }
    """
    fn = extract_function(atomic_src, "smp_test", type_model=tm)
    isir = emit_isir_module("smp_test", fn.state_vars, fn.effect)
    assert "conc_abstraction" in isir["module"]
    assert "LOS_AtomicAdd" in isir["module"]["conc_abstraction"]["atomic_actions"]

    plain_fn = extract_function(b"unsigned int plain(unsigned int x) { return x + 1; }", "plain", type_model=tm)
    plain_isir = emit_isir_module("plain", plain_fn.state_vars, plain_fn.effect)
    assert "conc_abstraction" not in plain_isir["module"]


def test_check_conc_abs_coherent():
    from litespec.interscope.dialects import check_conc_abs
    from litespec.schema.conc_abs_dialect import ConcAbsDialect

    d = ConcAbsDialect(context="atomic", atomic_actions=["LOS_AtomicAdd"])
    assert check_conc_abs(d).status == "pass"


def test_check_conc_abs_spinlock_requires_rg():
    from litespec.interscope.dialects import check_conc_abs
    from litespec.schema.conc_abs_dialect import ConcAbsDialect

    d = ConcAbsDialect(context="both", threads=["task", "isr"])  # rely/guarantee default "true"
    assert check_conc_abs(d).status == "fail"


def test_conc_abs_compatibility():
    from litespec.interscope.dialects import check_conc_abs_compatibility
    from litespec.schema.conc_abs_dialect import ConcAbsDialect

    a = ConcAbsDialect(context="both", threads=["task"], rely="P", guarantee="P")
    b = ConcAbsDialect(context="both", threads=["isr"], rely="P", guarantee="P")
    assert check_conc_abs_compatibility([a, b]).status == "pass"


def test_conc_abs_incompatibility():
    from litespec.interscope.dialects import check_conc_abs_compatibility
    from litespec.schema.conc_abs_dialect import ConcAbsDialect

    a = ConcAbsDialect(context="both", threads=["task"], rely="P", guarantee="Q")
    b = ConcAbsDialect(context="both", threads=["isr"], rely="P", guarantee="P")
    # a guarantees Q, but b relies on P → Q ⊄ P (both non-"true", unequal)
    assert check_conc_abs_compatibility([a, b]).status == "fail"
