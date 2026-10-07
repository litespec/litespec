"""Tests for the rliteos install script's Rust-target download logic."""

import subprocess

from litespec.targets import integration_path, load_target


def _script() -> str:
    return integration_path(load_target("liteos"), "targets/rliteos/install.sh").read_text(encoding="utf-8")


def _dist_ver(ver: str) -> str:
    """Run the install script's version→dist-name mapping for a rustc version."""
    script = f'''
        ver="{ver}"
        dist_ver="$ver"
        case "$ver" in
            *nightly*) dist_ver="nightly" ;;
        esac
        echo "$dist_ver"
    '''
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True).stdout.strip()


def test_dist_version_mapping():
    # the dist archive uses "nightly" for the nightly channel (not "1.95.0-nightly")
    assert _dist_ver("1.95.0-nightly") == "nightly"
    # stable and beta keep their full version number
    assert _dist_ver("1.92.0") == "1.92.0"
    assert _dist_ver("1.94.0-beta.1") == "1.94.0-beta.1"


def test_install_script_handles_nightly_and_mirrors():
    text = _script()
    assert "rsproxy.cn" in text
    assert "static.rust-lang.org" in text
    assert '*nightly*) dist_ver="nightly"' in text
    assert "multirust-channel-manifest.toml" in text
    assert "rust-std-$dist_ver-$RUST_TARGET.tar.xz" in text


def test_install_script_syntax():
    subprocess.run(["bash", "-n", integration_path(load_target("liteos"), "targets/rliteos/install.sh")], check=True)


def test_install_script_no_undefined_dist_server():
    # the removed shell variable must not leak as a reference (the env var
    # RUSTUP_DIST_SERVER is legitimate and still present)
    text = _script()
    assert "$DIST_SERVER" not in text
    assert "RUSTUP_DIST_SERVER=https://rsproxy.cn" in text


def test_interscope_install_clones_if_missing():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    text = (repo / "scripts" / "interscope.sh").read_text(encoding="utf-8")
    assert "git clone" in text
    assert "INTERSCOPE_REPO" in text
    assert "https://github.com/ywci/interscope" in text
    # clone only when the directory is absent (never clobber a manual copy)
    assert 'if [ ! -d "${IS_ROOT}" ]' in text
    # still records the pin, then installs InterScope's own dependencies
    assert "interscope_pin.yaml" in text
    assert 'bash "${IS_ROOT}/install.sh"' in text
    # deps install is best-effort (a missing opam must not undo the pin)
    assert "WARNING" in text
    subprocess.run(["bash", "-n", str(repo / "scripts" / "interscope.sh")], check=True)


def test_root_install_includes_interscope_by_default():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    text = (repo / "install.sh").read_text(encoding="utf-8")
    assert 'MODE="all"' in text
    assert "scripts/interscope.sh" in text
    # opt-out flags still available
    assert "--python-only" in text
    assert "--interscope-only" in text
    # --configure-llm forwards the LLM provider flag to scripts/interscope.sh
    assert "--configure-llm" in text
    assert "IS_FLAGS" in text
    subprocess.run(["bash", "-n", str(repo / "install.sh")], check=True)


def test_interscope_configure_llm_option():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    text = (repo / "scripts" / "interscope.sh").read_text(encoding="utf-8")
    assert "--configure-llm" in text
    assert "configure_llm()" in text
    # provider presets use env-var substitution (not a baked-in key)
    assert "deepseek-chat" in text
    assert "DEEPSEEK_API_KEY" in text
    assert "${" in text
