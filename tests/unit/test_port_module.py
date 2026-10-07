"""Multi-function module porting."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from litespec.lowering import port_module

_C = """\
#define SIZE 128
unsigned int helper(unsigned int x) { return x + 1; }
unsigned int caller(unsigned int n) { return helper(n); }
"""


def test_port_module_real_cross_references():
    rust = port_module(_C, ["helper", "caller"])
    assert "pub unsafe fn helper" in rust
    assert "pub unsafe fn caller" in rust
    assert "helper(n)" in rust  # caller calls the ported helper (real call, not stub)
    assert "unimplemented!" not in rust  # no stubs remain: helper is ported


@pytest.mark.skipif(shutil.which("rustc") is None, reason="rustc not available")
def test_port_module_compiles():
    rust = port_module(_C, ["helper", "caller"])
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        src = Path(d) / "out.rs"
        rlib = Path(d) / "lib.rlib"
        src.write_text(rust, encoding="utf-8")
        proc = subprocess.run(
            ["rustc", "--edition", "2021", "--crate-type", "lib", str(src), "-o", str(rlib)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert rlib.exists()
