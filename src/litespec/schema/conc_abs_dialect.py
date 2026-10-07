"""§14.1 ``ConcAbsDialect`` — the rely-guarantee concurrency abstraction.

The ISIR dialect stack is ``LIRDialect | MemAbsDialect | ConcAbsDialect | ISIRDialect``.
``ConcAbsDialect`` models the *concurrent* fragment (``Atomic`` / ``Concurrent`` /
``ISR``) as a rely-guarantee contract: ``rely`` is the environment's allowed
interference, ``guarantee`` is the component's own interference obligation, and
``atomic_actions`` are the indivisible transitions exempt from interference.
"""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel


class ConcAbsDialect(LiteSpecModel):
    """Rely-guarantee abstraction of the concurrent fragment."""

    context: str  # "atomic" | "both" | "isr" — the concurrency context
    threads: list[str] = []  # concurrent component identifiers
    rely: str = "true"  # environment interference predicate (R)
    guarantee: str = "true"  # own interference obligation (G)
    atomic_actions: list[str] = []  # indivisible ISIR actions (exempt from interference)
    notes: Optional[str] = None
