"""ISIR dialects.

The stack is ``LIRDialect | MemAbsDialect | ConcAbsDialect | ISIRDialect``.
``ConcAbsDialect`` (the rely-guarantee concurrency abstraction) is derived from the
LIR's atomic/spin-lock/per-CPU constructs and composition-checked; see ``conc_abs``.
"""

from litespec.interscope.dialects.conc_abs import (
    check_conc_abs,
    check_conc_abs_compatibility,
    derive_conc_abs_dialect,
)

__all__ = ["check_conc_abs", "check_conc_abs_compatibility", "derive_conc_abs_dialect"]
