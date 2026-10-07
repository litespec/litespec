"""Rule registry: ``@rule`` / ``@derivation_rule`` decorators (Phase 0)."""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from litespec.utils.failure_modes import FailureMode


@dataclass(frozen=True)
class Rule:
    """A registered normative rule or derivation rule."""

    id: str
    name: str
    classification: str  # "N" | "A"
    func: Callable[..., Any] = field(repr=False)
    section: Optional[str] = None
    failure_mode: Optional[str] = None
    is_derivation: bool = False


class RuleRegistry:
    """Global registry of ``@rule`` / ``@derivation_rule`` decorated functions."""

    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(
        self,
        rule_id: str,
        classification: str = "N",
        *,
        section: Optional[str] = None,
        failure_mode: Optional[str] = None,
        is_derivation: bool = False,
        name: Optional[str] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)

            self._rules[rule_id] = Rule(
                id=rule_id,
                name=name or func.__name__,
                classification=classification.upper(),
                func=wrapper,
                section=section,
                failure_mode=failure_mode,
                is_derivation=is_derivation,
            )
            return wrapper

        return decorator

    def get(self, rule_id: str) -> Optional[Rule]:
        return self._rules.get(rule_id)

    def all(self) -> tuple[Rule, ...]:
        return tuple(self._rules.values())

    def by_classification(self, classification: str) -> tuple[Rule, ...]:
        return tuple(r for r in self._rules.values() if r.classification == classification.upper())

    def __len__(self) -> int:
        return len(self._rules)


#: The singleton rule registry.
registry = RuleRegistry()


def rule(
    rule_id: str,
    classification: str = "N",
    *,
    section: Optional[str] = None,
    failure_mode: Optional[str] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a normative rule.

    Usage::

        @rule("R79", "N", section="§5.2", failure_mode="abi_entry_unbound")
        def abi_entry_coverage(spec): ...
    """
    return registry.register(rule_id, classification, section=section, failure_mode=failure_mode)


def derivation_rule(
    rule_id: str,
    classification: str = "N",
    *,
    section: Optional[str] = None,
    failure_mode: Optional[str] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a derivation rule (§13 D1–D95)."""
    return registry.register(rule_id, classification, section=section, failure_mode=failure_mode, is_derivation=True)


def resolve_failure_mode(failure_mode: Optional[str]) -> Optional[FailureMode]:
    """Resolve a failure-mode identifier to its enum member (or None)."""
    if failure_mode is None:
        return None
    try:
        return FailureMode[failure_mode]
    except KeyError:
        return None
