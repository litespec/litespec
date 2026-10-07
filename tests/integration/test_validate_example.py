"""Integration: the ``validate`` command loads the §18.1 example without error."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_validate_command_exit_zero(mm_search_typed_binder_path):
    proc = subprocess.run(
        [sys.executable, "-m", "litespec", "validate", str(mm_search_typed_binder_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK:" in proc.stdout
