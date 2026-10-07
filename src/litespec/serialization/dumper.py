"""YAML dumping of schema models back to ``.litespec.yaml`` text."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml

from litespec.schema.document import LiteSpecDocument


def dumps_litespec(doc: LiteSpecDocument, *, exclude_none: bool = True) -> str:
    """Serialize a ``LiteSpecDocument`` to canonical YAML text."""
    data = doc.model_dump(mode="json", exclude_none=exclude_none, by_alias=True)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)


def dump_litespec(doc: LiteSpecDocument, path: Union[str, Path], *, exclude_none: bool = True) -> None:
    """Write a ``LiteSpecDocument`` to a ``.litespec.yaml`` file."""
    Path(path).write_text(dumps_litespec(doc, exclude_none=exclude_none), encoding="utf-8")
