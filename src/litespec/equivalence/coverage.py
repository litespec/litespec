"""Verification-coverage classification and reporting (Phase 8).

Classifies each ported function by the *strongest* check that currently discharges
for it, so the coverage of a ported target is measurable rather than assumed:

- ``differential`` — pure function, C compiled and observed to agree with the LIR.
- ``concrete``    — pure function, LIR concretely evaluated (no C comparison).
- ``structural``  — impure (calls/memory/loops): non-trivial LIR + Rust compiles + ISIR validates.
- ``mismatch``    — a differential check disagreed (verification failure).
"""

from __future__ import annotations

from litespec.extraction import extract_function


def _prepare(c_source, config):
    """Build the shared fn table + field offsets + embedded fields once."""
    from litespec.equivalence.differential import build_fn_table
    from litespec.extraction import parse_c
    from litespec.extraction.struct_table import StructTable

    fn_table = build_fn_table(c_source, config=config)
    struct_table = StructTable.from_translation_unit(parse_c(c_source))
    return fn_table, struct_table.field_offsets(), struct_table.embedded_fields()


def classify_function(
    c_source: str | bytes,
    name: str,
    type_model=None,
    config=None,
    fn_table=None,
    field_offsets=None,
    embedded_fields=None,
) -> str:
    """Return the strongest verification level for one function."""
    from litespec.equivalence.differential import differential_check
    from litespec.equivalence.lir_interp import (
        is_interpretable,
        set_embedded_fields,
        set_field_offsets,
        set_fn_table,
        set_identity_casts,
    )

    fn = extract_function(c_source, name, type_model=type_model, config=config)
    if fn_table is None or field_offsets is None or embedded_fields is None:
        fn_table, field_offsets, embedded_fields = _prepare(c_source, config)
    set_fn_table(fn_table)
    set_field_offsets(field_offsets)
    set_embedded_fields(embedded_fields)
    # Identity casts (typedefs parsed as functional-cast calls) derive from the type model.
    from litespec.type_mapping import default_type_model

    tm = type_model or default_type_model()
    set_identity_casts(n for n, l in tm.c_to_lir.items() if l != "Unit")
    # MMIO macro names are target-config-driven; register them before interpretation.
    from litespec.intrinsics import register_mmio_from_target

    register_mmio_from_target()

    if not is_interpretable(fn.effect):
        return "structural"
    status, _ = differential_check(c_source, fn, fn_table=fn_table, tm=tm)
    if status == "ok":
        return "differential"
    if status == "mismatch":
        return "mismatch"
    return "concrete"  # interpretable but no C comparison (no clang / no struct-layout harness)


def coverage_report(c_source: str | bytes, function_names: list[str], type_model=None, config=None):
    """Return ``(level_counts, per_function_levels)``."""
    fn_table, field_offsets, embedded_fields = _prepare(c_source, config)
    counts: dict[str, int] = {}
    per_fn: dict[str, str] = {}
    for name in function_names:
        level = classify_function(
            c_source,
            name,
            type_model=type_model,
            config=config,
            fn_table=fn_table,
            field_offsets=field_offsets,
            embedded_fields=embedded_fields,
        )
        per_fn[name] = level
        counts[level] = counts.get(level, 0) + 1
    return counts, per_fn


def format_coverage(counts: dict[str, int], total: int) -> str:
    """Human-readable coverage summary."""
    order = ["differential", "concrete", "structural", "mismatch"]
    lines = []
    for level in order:
        n = counts.get(level, 0)
        pct = (100.0 * n / total) if total else 0.0
        lines.append(f"  {level:<13} {n:>3}  ({pct:5.1f}%)")
    return "\n".join(lines)
