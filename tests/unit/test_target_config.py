"""Target requirements configuration (config/targets/)."""

import pytest

from litespec.targets import available_targets, fetch_source, isir_output_dir, load_target
from litespec.targets.loader import TargetRequirements


def test_available_targets():
    assert "liteos" in available_targets()


def test_load_target():
    target = load_target("liteos")
    assert target.name == "liteos"
    assert target.port_name == "rliteos"
    assert target.source_repo.endswith("kernel_liteos_a")
    assert target.source_commit
    assert len(target.source_commit) == 40  # a real git SHA-1, not a placeholder
    assert target.manifest_repo.endswith("openharmony/manifest.git")
    assert target.manifest_branch == "master"
    assert target.modules["kernel_mm"] == ["LOS_MemAlloc", "LOS_MemFree", "LOS_MemAllocAlign"]
    assert target.modules["kernel_ipc"] == ["LOS_QueueWrite"]
    assert "gpu_drm" not in target.modules  # deferred (separate OpenHarmony service)
    assert target.module_for_function("LOS_MemAlloc") == "kernel_mm"
    assert target.module_for_function("nope") is None


def test_target_word_bits():
    from litespec.targets.loader import type_model_for

    tm = type_model_for(load_target("liteos"))
    assert tm.word_bits == 32  # LiteOS-A is a 32-bit target


def test_functions_in_scope():
    target = load_target("liteos")
    fns = target.functions_in_scope()
    assert len(fns) == 7  # 3×kernel_mm + sched + ipc + pm + vm (syscall/drm deferred)
    assert "LOS_MemAlloc" in fns
    assert "LOS_ArchMmuQuery" in fns


def test_isir_output_dir():
    target = load_target("liteos")
    assert str(isir_output_dir(target)).endswith("targets/rliteos/spec")


def test_rust_target_dir_is_target_board_support():
    from litespec.targets import integration_dir, rust_target_dir

    target = load_target("liteos")
    # the Rust port lives in the board-support folder, not a generic rust-target/
    assert rust_target_dir(target) == integration_dir(target)
    assert str(rust_target_dir(target)).endswith("targets/rliteos")


def test_fetch_source_requires_repo():
    target = TargetRequirements(name="x", source_repo="", source_commit="", modules={})
    with pytest.raises(ValueError):
        fetch_source(target)


def test_liteos_target_type_model_and_preprocess():
    target = load_target("liteos")
    assert target.type_model == "liteos"
    assert "LOSCFG_SYS_EXTERNAL_HEAP" in target.preprocess_defines


def test_liteos_target_testing_config():
    target = load_target("liteos")
    tc = target.testing
    assert tc.differential_compiler == "clang"
    assert tc.input_domains == [0, 1, 2, 7, 64, 128]
    assert tc.max_inputs == 64
    assert tc.fail_on_mismatch is True
    assert tc.required_differential == []
    assert tc.generated_tests_output == "tests/generated/test_liteos.py"
