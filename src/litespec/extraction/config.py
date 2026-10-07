"""Compile-time configuration model (Phase 2).

LiteOS-A's Kconfig generates ``LOSCFG_*`` macros (plus ``__LP64__``) that control
``#if`` / ``#ifdef`` / ``#ifndef`` conditional compilation. This module models that
configuration so the extractor selects the *active* branch instead of silently
dropping both branches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Config:
    """A set of defined macro names and integer macro values for ``#if`` evaluation."""

    defined: set[str] = field(default_factory=set)
    values: dict[str, int] = field(default_factory=dict)

    def is_defined(self, name: str) -> bool:
        return name in self.defined

    @classmethod
    def liteos_default(cls) -> Config:
        """A representative LiteOS-A configuration: VM on, 64-bit, LMS/leakcheck/waterline off."""
        return cls(
            defined={"LOSCFG_KERNEL_VM", "__LP64__"},
            values={"OS_MEM_EXPAND_ENABLE": 1, "OS_MEM_FREE_BY_TASKID": 0},
        )


def eval_pp_condition(expr: str, config: Config, macro_values: dict[str, int] | None = None) -> bool:
    """Evaluate a ``#if`` condition (a single identifier/integer, or ``defined(NAME)``)."""
    s = expr.strip()
    macro_values = macro_values or {}
    if re.fullmatch(r"[0-9]+", s):
        return int(s) != 0
    if re.fullmatch(r"[A-Za-z_]\w*", s):
        if s in config.values:
            return config.values[s] != 0
        if s in macro_values:
            return int(macro_values[s]) != 0
        return config.is_defined(s)  # C: undefined identifier → 0
    m = re.fullmatch(r"defined\s*\(\s*([A-Za-z_]\w*)\s*\)", s)
    if m:
        return config.is_defined(m.group(1))
    # Conservative fallback for complex expressions: treat as true.
    return True
