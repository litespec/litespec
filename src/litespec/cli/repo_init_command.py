"""``repo-init`` command: initialize the full OpenHarmony manifest via the ``repo`` tool."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from litespec.targets import available_targets, load_target, resolve_target

#: ``git-repo`` source mirror (the default Google Gerrit is often unreachable).
DEFAULT_REPO_URL = "https://mirrors.tuna.tsinghua.edu.cn/git/git-repo/"


def repo_init_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="litespec repo-init", description="Initialize the OpenHarmony manifest")
    parser.add_argument("target", nargs="?", default=None, help="target name (config/targets/<name>.yaml)")
    args = parser.parse_args(argv)

    target_name = resolve_target(args.target)
    if target_name not in available_targets():
        print(f"unknown target {target_name!r}; available: {available_targets()}", file=sys.stderr)
        return 2

    target = load_target(target_name)
    if not target.manifest_repo:
        print(f"target {target_name!r} has no manifest_repo configured", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parents[3]  # repo root
    repo_tool = root / "scripts" / "repo"
    dest = root / "third_party" / "openharmony"
    dest.mkdir(parents=True, exist_ok=True)

    if not repo_tool.is_file():
        print(f"repo tool not found at {repo_tool}; run the rliteos install first", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env.setdefault("REPO_URL", DEFAULT_REPO_URL)

    subprocess.run(
        [str(repo_tool), "init", "-u", target.manifest_repo, "-b", target.manifest_branch],
        cwd=dest,
        check=True,
        env=env,
    )
    print(f"repo init done → {dest}")
    print("next (large): cd third_party/openharmony && ../../scripts/repo sync -c -j8")
    return 0
