"""Rust struct emission (Phase 4): generate ``#[repr(C)] struct`` definitions."""

from __future__ import annotations

from litespec.extraction.c_parser import parse_c
from litespec.extraction.struct_table import StructField, StructTable
from litespec.lowering.rust_type_mapping import rust_type
from litespec.type_mapping import TypeModel, default_type_model


def _field_rust_type(field: StructField, tm: TypeModel) -> str:
    base = rust_type(tm.c_type_to_lir(field.base_type))
    if field.is_pointer:
        return f"*mut {base}"
    if field.array_size is not None:
        return f"[{base}; {field.array_size}]"
    return base


def render_structs(table: StructTable, type_model: TypeModel | None = None) -> str:
    """Render Rust ``#[repr(C)] struct`` definitions for a struct table."""
    tm = type_model or default_type_model()
    blocks: list[str] = []
    for name in sorted(table.structs):
        lines = ["#[repr(C)]", f"pub struct {name} {{"]
        for f in table.structs[name]:
            lines.append(f"    pub {f.name}: {_field_rust_type(f, tm)},")
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def struct_definitions(c_source: str | bytes, type_model: TypeModel | None = None) -> str:
    """Extract and render Rust struct definitions from C source (convenience)."""
    tu = parse_c(c_source)
    table = StructTable.from_translation_unit(tu)
    return render_structs(table, type_model)
