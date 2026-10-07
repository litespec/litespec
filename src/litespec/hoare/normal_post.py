"""Normal post and halt conditions (§9.21.4 ``normal_post_of`` / ``halt_of``)."""

from __future__ import annotations

from litespec.schema.hoare_triple import HoareTriple
from litespec.schema.primitives import Predicate


def halt_of(t: HoareTriple) -> Predicate:
    """The halt condition: disjunction of exit disjunct conditions ∧ posts."""
    exits = t.exit_state.disjuncts if t.exit_state is not None else []
    if not exits:
        return Predicate(expression="false", description="No halt path")
    expr = " or ".join(f"({d.condition.expression}) and ({d.post.expression})" for d in exits)
    return Predicate(expression=expr, description="Disjunction of halt conditions and their posts")


def normal_post_of(t: HoareTriple) -> Predicate:
    """``post ∧ ¬halt``."""
    halt = halt_of(t)
    return Predicate(
        expression=f"({t.post.expression}) and not ({halt.expression})",
        description="Normal post: postcondition conjoined with the negation of the halt condition",
    )
