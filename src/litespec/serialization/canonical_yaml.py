"""Canonical YAML serialization (stable, sorted-key) for hashing and reproducibility."""

from __future__ import annotations

import hashlib
from typing import Any

import yaml


def canonical_yaml(data: Any) -> str:
    """Return a canonical (sorted-key) YAML rendering of ``data``."""
    return yaml.safe_dump(data, sort_keys=True, allow_unicode=True, default_flow_style=False)


def canonical_hash(data: Any) -> str:
    """SHA-256 over the canonical YAML rendering of ``data``."""
    return hashlib.sha256(canonical_yaml(data).encode("utf-8")).hexdigest()
