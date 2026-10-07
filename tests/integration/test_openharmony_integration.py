"""Integration tests for OpenHarmony integration (kernel source + BUILD.gn + toolchain).

Validates that the rliteos port integrates with the real OpenHarmony kernel: the
fetched source contains the exact functions the port targets, the kernel's gn build
tree references them, and the generated ``BUILD.gn`` is structurally valid. Build-tool
tests (``gn``/``ninja``) are gated on the toolchain.
"""

import shutil
from pathlib import Path

import pytest

from litespec.build import generate_build_gn
from litespec.targets import load_target, third_party_dir

TARGET = load_target("liteos")
REPO = Path(__file__).resolve().parents[2]

KERNEL = third_party_dir(TARGET)  # third_party/liteos (the kernel_liteos_a tree)
LOS_MEMORY = KERNEL / "kernel" / "base" / "mem" / "tlsf" / "los_memory.c"
KERNEL_BASE_GN = KERNEL / "kernel" / "base" / "BUILD.gn"

#: The C functions the port validated against — these must exist in the real kernel.
PORTED_FUNCTIONS = [
    "OsMemFFS",
    "OsMemFLS",
    "OsMemLog2",
    "OsMemFlGet",
    "OsMemSlGet",
    "OsMemFreeListIndexGet",
    "LOS_MemAlloc",
    "LOS_MemAllocAlign",
    "LOS_MemFree",
]


def test_fetched_kernel_has_los_memory():
    if not KERNEL.is_dir():
        pytest.skip("kernel source not fetched (run: ./run.sh fetch-source liteos)")
    assert LOS_MEMORY.is_file()


def test_kernel_build_gn_references_los_memory():
    if not KERNEL_BASE_GN.is_file():
        pytest.skip("kernel source not fetched")
    text = KERNEL_BASE_GN.read_text(encoding="utf-8")
    # the real kernel's gn build compiles the file we ported from
    assert "mem/tlsf/los_memory.c" in text


def test_ported_functions_match_real_kernel():
    if not LOS_MEMORY.is_file():
        pytest.skip("kernel source not fetched")
    text = LOS_MEMORY.read_text(encoding="utf-8")
    missing = [f for f in PORTED_FUNCTIONS if f not in text]
    assert not missing, f"ported functions missing from real kernel: {missing}"


def test_generated_build_gn_is_structurally_valid():
    gn = generate_build_gn(TARGET)
    assert 'static_library("rliteos")' in gn
    assert "librliteos.a" in gn
    assert 'import("//build/lite/config/component/lite_component.gni")' in gn
    # balanced braces (a cheap syntactic sanity check for gn)
    assert gn.count("{") == gn.count("}")
    # the wrong hardcoded kernel include path must not leak in
    assert "//kernel/liteos_a" not in gn


def test_ninja_build_executor_installed():
    assert shutil.which("ninja") is not None


def test_gn_available():
    if shutil.which("gn") is None:
        pytest.skip("gn not available (ships in the OpenHarmony build repo)")
