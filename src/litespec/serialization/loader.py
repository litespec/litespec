"""YAML loading of ``.litespec.yaml`` documents into schema models."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Union

import yaml

from litespec.schema.document import LiteSpecDocument


def load_yaml_data(text: str) -> Any:
    """Parse YAML text into plain Python data."""
    return yaml.safe_load(text)


def loads_litespec(text: str) -> LiteSpecDocument:
    """Parse YAML text into a ``LiteSpecDocument`` (raising on schema errors)."""
    data = yaml.safe_load(text)
    if data is None:
        raise ValueError("empty .litespec.yaml document")
    return LiteSpecDocument.model_validate(data)


def load_litespec(path: Union[str, Path]) -> LiteSpecDocument:
    """Load a ``.litespec.yaml`` file into a ``LiteSpecDocument``."""
    p = Path(path)
    return loads_litespec(p.read_text(encoding="utf-8"))
