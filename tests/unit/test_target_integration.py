"""Target-integration configuration (config/targets/liteos.yaml → targets/rliteos/).

Verifies the config-driven board/arch support: the target declares its toolchain
triple, arch assembly files, linker script, UART stub, build template, QEMU
parameters, and a unique command entry point by relative path; every referenced
file resolves to the repo root, and the default (checked-in) files are separated
from the dynamically generated artifacts cleaned by ``./run.sh clean``.
"""

from pathlib import Path

from litespec.targets import (
    integration_dir,
    load_target,
    resolved_integration_files,
    target_entrypoint,
)

#: The checked-in "default" files in targets/rliteos/ (everything else is generated).
DEFAULT_FILES = {
    "BUILD.gn",
    "run.sh",
    "install.sh",
    "README.md",
    "liteos.ld",
    "drivers/uart_pl011.rs",
    ".gitignore",
    "arch/reset_vector.S",
    "arch/task_switch.S",
}


def test_target_integration_fields_load():
    target = load_target("liteos")
    assert target.target_triple == "armv7a-none-eabi"
    assert target.asm_files == [
        "targets/rliteos/arch/reset_vector.S",
        "targets/rliteos/arch/task_switch.S",
    ]
    assert target.linker_script == "targets/rliteos/liteos.ld"
    assert target.uart_stub == "targets/rliteos/drivers/uart_pl011.rs"
    assert target.build_system == "gn"
    assert target.build_template == "targets/rliteos/BUILD.gn"
    assert target.qemu_machine == "virt"
    assert target.qemu_cpu == "cortex-a15"
    assert target.qemu_memory == "128M"
    assert target.entrypoint == "targets/rliteos/run.sh"


def test_integration_dir_is_port_name_based():
    target = load_target("liteos")
    assert integration_dir(target).name == "rliteos"
    assert str(integration_dir(target)).endswith("targets/rliteos")


def test_all_declared_integration_files_exist():
    target = load_target("liteos")
    files = resolved_integration_files(target)
    assert files  # the target declares integration artifacts
    missing = [str(p) for p in files.values() if not p.is_file()]
    assert not missing, f"declared integration files missing: {missing}"


def test_target_entrypoint_resolves():
    entry = target_entrypoint(load_target("liteos"))
    assert entry is not None
    assert entry.name == "run.sh"
    assert str(entry).endswith("targets/rliteos/run.sh")
    assert entry.is_file()


def test_entrypoint_is_executable():
    import os

    entry = target_entrypoint(load_target("liteos"))
    assert os.access(entry, os.X_OK)


def test_default_files_are_present():
    from litespec.targets import integration_path

    target = load_target("liteos")
    for rel in DEFAULT_FILES:
        assert integration_path(target, f"targets/rliteos/{rel}").exists(), rel


def test_gitignore_covers_generated_patterns():
    from litespec.targets import integration_path

    target = load_target("liteos")
    gi = integration_path(target, "targets/rliteos/.gitignore").read_text(encoding="utf-8")
    assert "build/" in gi


def test_install_script_declares_dependencies():
    from litespec.targets import integration_path

    target = load_target("liteos")
    text = integration_path(target, "targets/rliteos/install.sh").read_text(encoding="utf-8")
    assert "qemu-system-arm" in text
    assert "armv7a-none-eabi" in text
    assert "rustup target add" in text
    # cross-platform: macOS (Homebrew) + Ubuntu/Debian (apt-get)
    assert "brew install" in text
    assert "apt-get install" in text
    assert "uname -s" in text
    # OpenHarmony toolchain is an opt-in phase (multi-GB), not the default install
    assert "--with-openharmony" in text
    assert "prebuilts_download.sh" in text
    assert "prebuilts/build-tools" in text
    assert "prebuilts_config.py" in text


def test_entrypoint_clean_removes_generated_artifacts():
    """The target's run.sh clean deletes build/ but keeps the default files."""
    import subprocess

    target = load_target("liteos")
    entry = target_entrypoint(target)
    base = Path(entry).parent
    # simulate generated artifacts under build/
    (base / "build").mkdir(exist_ok=True)
    (base / "build" / "rliteos.elf").write_text("ELF", encoding="utf-8")
    (base / "build" / "reset_vector.o").write_text("OBJ", encoding="utf-8")
    subprocess.run([str(entry), "clean"], check=True, capture_output=True, text=True)
    assert not (base / "build").exists()
    # the default (source) files are untouched
    for rel in DEFAULT_FILES:
        assert (base / rel).exists(), rel


def test_linker_script_references_entry_symbol():
    target = load_target("liteos")
    ld = resolved_integration_files(target)[target.linker_script]
    text = Path(ld).read_text(encoding="utf-8")
    assert "ENTRY(_start)" in text
    assert "__stack_top" in text


def test_emit_baremetal_scaffolding():
    from litespec.extraction import parse_c
    from litespec.extraction.c_translation_unit import functions
    from litespec.lowering import emit_baremetal
    from litespec.type_mapping import load_type_model

    src = b"typedef unsigned int UINT32;\nUINT32 add(UINT32 a, UINT32 b) { return a + b; }"
    fns = [f.name for f in functions(parse_c(src)) if f.name]
    target = load_target("liteos")
    rust = emit_baremetal(src, fns, target, type_model=load_type_model("liteos"))
    # no_std boot scaffolding + volatile memory model (no host-sim MEM array)
    assert "#![no_std]" in rust
    assert "#![no_main]" in rust
    assert "static mut MEM" not in rust
    assert "read_volatile" in rust
    # arch .S assembled separately, panic handler, UART stub, entry point — from config
    assert "targets/rliteos/arch/reset_vector.S" in rust
    assert "targets/rliteos/arch/task_switch.S" in rust
    assert "#[panic_handler]" in rust
    assert 'include!("targets/rliteos/drivers/uart_pl011.rs");' in rust
    assert 'pub extern "C" fn rmain() -> !' in rust
    # the ported function is still emitted
    assert "pub unsafe fn add" in rust
