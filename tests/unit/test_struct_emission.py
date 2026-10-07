"""Struct definition extraction + Rust emission."""

from litespec.extraction import parse_c
from litespec.extraction.struct_table import StructField, StructTable
from litespec.lowering.struct_emission import render_structs, struct_definitions

_SRC = "struct OsMemNodeHead { unsigned int sizeAndFlag; struct OsMemNodeHead *next; unsigned int array[8]; };\n"


def test_struct_table_extracts_fields():
    tu = parse_c(_SRC.encode())
    table = StructTable.from_translation_unit(tu)
    fields = table.structs["OsMemNodeHead"]
    assert fields[0] == StructField("sizeAndFlag", "unsigned int")
    assert fields[1] == StructField("next", "struct OsMemNodeHead", is_pointer=True)
    assert fields[2] == StructField("array", "unsigned int", array_size=8, is_array=True)


def test_render_structs():
    tu = parse_c(_SRC.encode())
    table = StructTable.from_translation_unit(tu)
    rust = render_structs(table)
    assert "pub struct OsMemNodeHead {" in rust
    assert "pub sizeAndFlag: u64," in rust
    assert "pub next: *mut OsMemNodeHead," in rust
    assert "pub array: [u64; 8]," in rust


def test_struct_definitions_convenience():
    rust = struct_definitions(_SRC)
    assert "pub struct OsMemNodeHead {" in rust
    assert "*mut OsMemNodeHead" in rust
