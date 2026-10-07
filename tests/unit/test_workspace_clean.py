"""Workspace cleanliness: .gitignore coverage + run.sh --clean."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_gitignore_covers_generated_artifacts():
    gi = (REPO / ".gitignore").read_text(encoding="utf-8")
    for pattern in (
        "*.rlib",
        "*.a",
        "*.o",
        "*.elf",
        "*.bin",
        "kernel_mm/",
        "output/",
        "tmp*",
        "temp*",
        ".uv-cache/",
        ".uv-python/",
        ".uv-bin/",
        ".python-version",
        "third_party/",
        ".repo-home/",
        "targets/rliteos/build/",
    ):
        assert pattern in gi, pattern


def test_run_sh_has_comprehensive_clean():
    run = (REPO / "run.sh").read_text(encoding="utf-8")
    assert "clean|--clean)" in run
    assert "cleaned workspace" in run
    # clean removes the whole re-fetchable third_party/ tree + the dev env is kept
    assert "rm -rf third_party .repo-home" in run
    assert "kept .venv" in run
    # clean --all additionally drops the repo-local env + toolchain
    assert "rm -rf .venv .python-version" in run
    assert "rm -rf .tools" in run
    # clean stays within the repo (workspace-root artifacts are out of scope)
    assert "../.rustsysroot" not in run
    # clean removes stray temp dirs too
    assert "tmp* temp*" in run
    # build/qemu/asm still delegate to the target entry point
    assert "build|qemu|asm)" in run
    assert "target_entrypoint" in run


def test_run_sh_syntax():
    import subprocess

    subprocess.run(["bash", "-n", str(REPO / "run.sh")], check=True)


def test_src_interscope_is_source_not_generated():
    """src/litespec/interscope is pipeline source (not a cleanable copy)."""
    init = REPO / "src" / "litespec" / "interscope" / "__init__.py"
    assert init.is_file()
    text = init.read_text(encoding="utf-8")
    assert "InterScope integration" in text
