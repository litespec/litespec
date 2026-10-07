"""OpenHarmony BUILD.gn generation (config-driven)."""

from litespec.build_gn import generate_build_gn
from litespec.targets import load_target


def test_generate_build_gn_is_config_driven():
    target = load_target("liteos")
    gn = generate_build_gn(target)
    # target named after port_name, not the source target
    assert 'static_library("rliteos")' in gn
    # arch .S files + the Rust static library are listed as sources
    for rel in target.asm_files:
        assert f'"{rel}"' in gn
    assert "targets/rliteos/librliteos.a" in gn
    # toolchain + board values flow through from config
    assert target.target_triple in gn
    assert "-mcpu=cortex-a15" in gn
    assert "linker_script:" in gn


def test_generate_build_gn_matches_cli():
    import subprocess
    import sys

    target = load_target("liteos")
    expected = generate_build_gn(target)
    proc = subprocess.run(
        [sys.executable, "-m", "litespec", "build-gn", "liteos"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == expected
