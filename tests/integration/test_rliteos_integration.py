"""Integration tests for the rliteos target (config → files → emit → compile → link → boot).

Validates the full integration layer end-to-end: the config resolves board files,
the bare-metal emitter produces a crate that compiles for ``armv7a-none-eabi``,
links with the arch ``.S`` files into an ELF image, and (when QEMU is present)
boots and prints ``hello from rliteos``.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.lowering import emit_baremetal
from litespec.targets import load_target, resolved_integration_files
from litespec.type_mapping import load_type_model

TARGET = load_target("liteos")
REPO = Path(__file__).resolve().parents[2]

#: bare-metal flags: abort on panic (no unwind) and drop volatile precondition checks.
RUSTC_FLAGS = ["-C", "panic=abort", "-C", "debug-assertions=off"]


def _file(rel: str) -> str:
    return resolved_integration_files(TARGET)[rel].read_text(encoding="utf-8")


def _emit() -> str:
    src = b"typedef unsigned int UINT32;\nUINT32 add(UINT32 a, UINT32 b) { return a + b; }"
    fns = [f.name for f in functions(parse_c(src)) if f.name]
    return emit_baremetal(src, fns, TARGET, type_model=load_type_model(TARGET.type_model))


def _have_arm_target() -> bool:
    """armv7a-none-eabi std is present (rustc can build for it)."""
    try:
        sysroot = subprocess.run(["rustc", "--print", "sysroot"], capture_output=True, text=True).stdout.strip()
    except FileNotFoundError:
        return False
    return (Path(sysroot) / "lib" / "rustlib" / "armv7a-none-eabi" / "lib").is_dir()


def _have_lld() -> bool:
    return shutil.which("ld.lld") is not None


def _have_qemu() -> bool:
    return shutil.which("qemu-system-arm") is not None


def _build_image(d: Path) -> Path:
    """Emit → compile (rustc) → assemble (.S) → link (ld.lld) → ELF, in dir ``d``."""
    # symlink targets/ so the emitted `include!("targets/rliteos/…")` resolves
    os.symlink(REPO / "targets", d / "targets")
    main_rs = d / "main.rs"
    main_rs.write_text(_emit(), encoding="utf-8")
    main_o = d / "main.o"
    subprocess.run(
        ["rustc", "--target", "armv7a-none-eabi", *RUSTC_FLAGS, "--emit=obj", str(main_rs), "-o", str(main_o)],
        check=True,
        capture_output=True,
    )
    objs = [main_o]
    for rel in TARGET.asm_files:
        src = resolved_integration_files(TARGET)[rel]
        obj = d / (Path(rel).stem + ".o")
        subprocess.run(
            ["clang", "--target=armv7a-none-eabi", "-c", str(src), "-o", str(obj)],
            check=True,
            capture_output=True,
        )
        objs.append(obj)
    elf = d / "rliteos.elf"
    subprocess.run(
        [
            "ld.lld",
            "-T",
            str(resolved_integration_files(TARGET)[TARGET.linker_script]),
            *(str(o) for o in objs),
            "-o",
            str(elf),
        ],
        check=True,
        capture_output=True,
    )
    return elf


def _boot(elf: Path, timeout_s: int = 8) -> str:
    """Boot the ELF in QEMU and return its serial output."""
    proc = subprocess.Popen(
        ["qemu-system-arm", "-machine", "virt", "-cpu", "cortex-a15", "-m", "128M", "-nographic", "-nic", "none", "-kernel", str(elf)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        out, _ = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
    return out


# ---- always-run (no toolchain) -------------------------------------------------


def test_config_to_files_to_emit():
    files = resolved_integration_files(TARGET)
    assert files
    assert all(p.is_file() for p in files.values())


def test_emitted_crate_references_target_files():
    rust = _emit()
    assert "#![no_std]" in rust
    assert "#![no_main]" in rust
    assert f'include!("{TARGET.uart_stub}");' in rust
    assert 'pub extern "C" fn rmain() -> !' in rust


def test_symbol_contract_across_linker_asm_rust():
    ld = _file(TARGET.linker_script)
    reset = _file(TARGET.asm_files[0])
    switch = _file(TARGET.asm_files[1])
    rust = _emit()
    assert "ENTRY(_start)" in ld
    assert ".global _start" in reset
    assert "bl  rmain" in reset
    assert 'pub extern "C" fn rmain() -> !' in rust
    for sym in ("__stack_top", "__bss_start", "__bss_end"):
        assert sym in ld
        assert sym in reset
    assert ".global HalTaskSwitch" in switch


def test_asm_files_assemble_with_clang():
    for rel in TARGET.asm_files:
        path = resolved_integration_files(TARGET)[rel]
        proc = subprocess.run(
            ["clang", "--target=armv7a-none-eabi", "-c", str(path), "-o", "/dev/null"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr


# ---- toolchain-gated -----------------------------------------------------------


@pytest.mark.skipif(not _have_arm_target(), reason="armv7a-none-eabi target not installed")
def test_emitted_crate_compiles():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        os.symlink(REPO / "targets", d / "targets")
        main_rs = d / "main.rs"
        main_rs.write_text(_emit(), encoding="utf-8")
        obj = d / "main.o"
        subprocess.run(
            ["rustc", "--target", "armv7a-none-eabi", *RUSTC_FLAGS, "--emit=obj", str(main_rs), "-o", str(obj)],
            check=True,
            capture_output=True,
        )
        assert obj.is_file()


@pytest.mark.skipif(not _have_arm_target() or not _have_lld(), reason="armv7a-none-eabi/lld not installed")
def test_link_step_produces_bootable_elf():
    with tempfile.TemporaryDirectory() as tmp:
        elf = _build_image(Path(tmp))
        assert elf.is_file()
        assert elf.read_bytes()[:4] == b"\x7fELF"


@pytest.mark.skipif(not _have_qemu(), reason="qemu-system-arm not installed")
@pytest.mark.skipif(not _have_arm_target() or not _have_lld(), reason="armv7a-none-eabi/lld not installed")
def test_boot_in_qemu_prints_hello():
    with tempfile.TemporaryDirectory() as tmp:
        elf = _build_image(Path(tmp))
        out = _boot(elf)
        assert "hello from rliteos" in out
