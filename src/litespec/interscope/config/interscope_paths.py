"""InterScope path configuration (interscope.md §2.3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_PIN_CONFIG = _PROJECT_ROOT / "config" / "interscope" / "interscope_pin.yaml"
_THIRD_PARTY = _PROJECT_ROOT / "third_party" / "interscope"

_DEFAULT: dict[str, Any] = {
    "root": str(_THIRD_PARTY),
    "entry_point": str(_THIRD_PARTY / "run.sh"),
    "schema": str(_THIRD_PARTY / "conf" / "schemas" / "isir_schema.yaml"),
    "trace_schema": str(_THIRD_PARTY / "conf" / "schemas" / "trace_schema.yaml"),
    "config": str(_THIRD_PARTY / "conf" / "config.yaml"),
    "commit": "unknown",
    "isir_schema_version": "0.1",
}


def _config() -> dict[str, Any]:
    if not _PIN_CONFIG.exists():
        return dict(_DEFAULT)
    data = yaml.safe_load(_PIN_CONFIG.read_text(encoding="utf-8")) or {}
    merged = dict(_DEFAULT)
    merged.update(data.get("interscope", {}))
    return merged


def interscope_root() -> str:
    return str(_config()["root"])


def interscope_entry_point() -> str:
    return str(_config()["entry_point"])


def interscope_schema() -> str:
    return str(_config()["schema"])


def interscope_commit() -> str:
    return str(_config()["commit"])


def project_root() -> Path:
    return _PROJECT_ROOT
