"""Source layer schema (§5)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel


class SourceLayer(LiteSpecModel):
    """§5.1 ``SourceLayer ::= { file, function?, functions?, line_range, excerpt, ... }``."""

    file: str
    function: Optional[str] = None
    functions: Optional[list[str]] = None
    line_range: list[int] = []
    excerpt: str = ""
    context_note: Optional[str] = None
    non_code_source: Optional[str] = None
    source_language: Optional[str] = None
