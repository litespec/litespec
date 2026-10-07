"""C preprocessing via ``clang -E -P`` (Phase 2).

Resolves ``#if``/``#ifdef``/``#define`` and inlines headers before extraction.
Configured by the target's ``preprocess`` section (defines + include dirs).
"""

from __future__ import annotations

import subprocess
from typing import Iterable, Mapping, Union


def preprocess_c(
    source: Union[str, bytes],
    defines: Mapping[str, object] | None = None,
    include_dirs: Iterable[str] = (),
) -> str:
    """Preprocess C source with clang, returning the expanded translation unit."""
    cmd = ["clang", "-E", "-P"]
    for key, value in (defines or {}).items():
        cmd.append(f"-D{key}={value}")
    for d in include_dirs:
        cmd.append(f"-I{d}")
    cmd += ["-x", "c", "-"]

    proc = subprocess.run(
        cmd,
        input=source if isinstance(source, bytes) else source.encode("utf-8"),
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"clang -E failed: {proc.stderr.decode('utf-8', errors='replace')[:500]}")
    return proc.stdout.decode("utf-8", errors="replace")
