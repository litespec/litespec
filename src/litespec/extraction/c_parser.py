"""C parser integration via tree-sitter-c (Phase 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import tree_sitter_c
from tree_sitter import Language, Node, Parser

_LANG = Language(tree_sitter_c.language())
_PARSER = Parser(_LANG)


def parse_c(source: Union[str, bytes]) -> Node:
    """Parse C source into a tree-sitter ``translation_unit`` node."""
    if isinstance(source, str):
        source = source.encode("utf-8")
    return _PARSER.parse(source).root_node


def parse_c_file(path: Union[str, Path]) -> Node:
    """Parse a C source file into a tree-sitter ``translation_unit``."""
    return parse_c(Path(path).read_bytes())


def c_language() -> Language:
    return _LANG
