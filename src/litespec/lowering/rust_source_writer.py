"""Rust source writing (Phase 4)."""

from __future__ import annotations

from pathlib import Path
from typing import Union


def write_rust_source(path: Union[str, Path], content: str) -> Path:
    """Write a Rust source file, creating parent directories as needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p
