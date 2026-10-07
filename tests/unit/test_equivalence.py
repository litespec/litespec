"""layered EC verification (five seams + refinement chain)."""

from litespec.equivalence import generate_obligations, observe, run_layered_ec, stronger_or_equal


def test_relation_lattice():
    assert stronger_or_equal("exact", "refinement_only")
    assert not stronger_or_equal("refinement_only", "exact")
    assert stronger_or_equal("bisimulation", "observational")


def test_observe():
    mapping = observe([("pool", "Nat"), ("cursor", "Block")], ["sig_pool", "sig_cursor"])
    assert mapping == {"sig_pool": "sigma.pool", "sig_cursor": "sigma.cursor"}


def test_generate_obligations():
    assert generate_obligations() == [
        "c_to_lir",
        "lir_to_unsafe",
        "unsafe_to_safe",
        "lir_to_isir",
        "safe_to_isir",
    ]


def test_run_layered_ec_without_artifacts_is_not_discharged():
    # No artifacts → every seam degrades to "warn" (never a silent "pass").
    result, chain = run_layered_ec()
    assert result.status == "warn"
    assert len(result.warnings) == 5
    assert chain.links == [
        "T_C ⊑ T_LIR",
        "T_LIR ⊑ T_Unsafe",
        "T_Unsafe ⊑ T_Safe",
        "T_LIR ⊑_α T_ISIR",
        "T_Safe ⊑_α T_ISIR",
    ]


def test_counterexample_classification():
    from litespec.equivalence.counterexample import Counterexample
    from litespec.equivalence.counterexample_classification import classify

    ce = Counterexample(kind="lir_to_isir", trace=(("sig_cursor", 0), ("sig_cursor", 1)))
    assert classify(ce) == "lir_to_isir"
