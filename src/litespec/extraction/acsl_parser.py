"""ACSL annotation parser (Phase 2).

Parses a minimal ACSL subset from C comments: ``requires``, ``ensures``,
``loop invariant``, and ``assigns`` clauses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AcslClause:
    kind: str  # "requires" | "ensures" | "loop_invariant" | "assigns"
    expression: str


_CLAUSE_RE = re.compile(r"(requires|ensures|loop\s+invariant|assigns)\s+(.+)", re.DOTALL)


def _strip_delimiters(text: str) -> str:
    body = re.sub(r"/\*\s*@?", "", text)
    body = re.sub(r"@?\s*\*/", "", body)
    body = re.sub(r"//\s*@?", "", body)
    return body.strip()


def parse_acsl(comment_text: str) -> list[AcslClause]:
    """Parse ACSL clauses from a single C comment's text."""
    body = _strip_delimiters(comment_text)
    if not body:
        return []
    clauses: list[AcslClause] = []
    for part in body.split(";"):
        part = part.strip()
        if not part:
            continue
        m = _CLAUSE_RE.match(part)
        if m:
            kind = re.sub(r"\s+", "_", m.group(1))
            clauses.append(AcslClause(kind=kind, expression=m.group(2).strip()))
    return clauses


def is_acsl_comment(comment_text: str) -> bool:
    """Whether a comment text carries an ACSL payload (``@`` marker)."""
    return "@" in comment_text
