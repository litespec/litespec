"""Smoke test for the ``liteos64`` 64-bit target (the word-width abstraction).

Verifies that a target config with ``word_bits: 64`` drives ``u64`` through the
type model, memory model, interpreter mask, and an end-to-end port — with the same
kernel source as the 32-bit target.
"""

import subprocess
import tempfile
from pathlib import Path

from litespec.equivalence import lir_interp as li
from litespec.extraction.config import Config
from litespec.intrinsics import Op
from litespec.lowering import port_module
from litespec.lowering.effect_expr_to_rust import memory_model
from litespec.targets.loader import available_targets, load_target
from litespec.type_mapping import load_type_model


def test_liteos64_type_model_is_64_bit():
    tm = load_type_model("liteos64")
    assert tm.word_bits == 64
    assert tm.word_type() == "u64"
    # the 32-bit model is unchanged
    assert load_type_model("liteos").word_type() == "u32"


def test_liteos64_target_config_loads():
    assert "liteos64" in available_targets()
    t = load_target("liteos64")
    assert t.type_model == "liteos64"
    assert t.target_triple == "aarch64-none-elf"
    assert t.mcpu == "cortex-a53"
    # the default target is still liteos (two targets → default wins)
    from litespec.targets.loader import resolve_target

    assert resolve_target() == "liteos"


def test_liteos64_memory_model_is_u64():
    mm = memory_model("u64", executable=True)
    assert "MEM: [u64; 65536]" in mm
    assert "MMIO: [u64; 65536]" in mm


def test_liteos64_interpreter_masks_to_64_bits():
    li.set_word_bits(64)
    try:
        assert li._mask(-1) == 0xFFFFFFFFFFFFFFFF
        assert li._clz(1) == 63
        mem: dict[int, int] = {}
        li._eval_intrinsic(Op.ATOMIC_STORE, [0x100, 0x1_0000_0000], mem)
        assert mem[0x100] == 0x100000000  # no 32-bit truncation
    finally:
        li.set_word_bits(32)


def test_liteos64_ports_u64_and_roundtrips():
    src = b"unsigned long read_word(unsigned long *p) { return *p; }\n"
    tm = load_type_model("liteos64")
    rust = port_module(src, ["read_word"], type_model=tm, config=Config(), executable=True)
    assert "u64" in rust  # the word type is u64, not u32
    rust += (
        "\nfn main() { unsafe {\n"
        "  let p: u64 = 0x100;\n"
        "  __write(p, 0x123456789ABCDEF0);\n"
        "  let r = read_word(p);\n"
        '  println!("r={:#x}", r);\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "smoke.rs"
        exe = Path(d) / "smoke"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        assert run.stdout.strip() == "r=0x123456789abcdef0"  # 64-bit value preserved


def test_liteos64_layered_ec_passes():
    """The five-seam EC runs green under the 64-bit model (u64 word width)."""
    from litespec.equivalence import verify_function

    src = b"unsigned long inc(unsigned long x) { return x + 1; }\n"
    tm = load_type_model("liteos64")
    result, chain = verify_function(src, "inc", type_model=tm)
    assert result.status == "pass", result.errors
    assert len(chain.links) == 5
    # the pure function is differentially verified on both concrete seams
    assert any("differentially verified" in r for r in result.reports), result.reports
