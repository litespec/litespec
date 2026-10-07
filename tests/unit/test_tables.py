"""Table modules: size table, global table, struct field offsets."""

from litespec.extraction import parse_c
from litespec.extraction.global_table import GlobalTable
from litespec.extraction.size_table import compute_sizes, sizeof_type
from litespec.extraction.struct_table import StructTable


def test_compute_sizes_primitives():
    sizes = compute_sizes(StructTable())
    assert sizeof_type("unsigned int", sizes) == 1  # 1 word
    assert sizeof_type("UINT32", sizes) == 1
    assert sizeof_type("unsigned char", sizes) == 1
    assert sizeof_type("unsigned long long", sizes) == 1
    assert sizeof_type("unsigned int *", sizes) == 1  # pointer = 1 word


def test_compute_sizes_struct_field_sum():
    tu = parse_c(b"struct A { unsigned int x; void *p; unsigned int y; };")
    sizes = compute_sizes(StructTable.from_translation_unit(tu))
    assert sizeof_type("A", sizes) == 3  # 3 fields = 3 words


def test_global_table_captures_file_scope_only():
    tu = parse_c(b"int g1 = 0; static int g2 = 0; int f(void) { int local = 0; return local; }")
    g = GlobalTable.from_translation_unit(tu)
    assert "g1" in g.names
    assert "g2" in g.names
    assert "local" not in g.names  # function-local is not a global
    assert "f" not in g.names  # function name is not a global


def test_struct_table_field_offsets():
    tu = parse_c(b"struct A { unsigned int x; unsigned int y; unsigned int z; };")
    offsets = StructTable.from_translation_unit(tu).field_offsets()
    assert offsets == {"x": 0, "y": 1, "z": 2}


def test_struct_table_scoped_field_offsets_and_types():
    tu = parse_c(b"struct A { unsigned int x; struct B b; };struct B { unsigned int x; unsigned int y; };")
    st = StructTable.from_translation_unit(tu)
    # Scoped offsets keep colliding ``x`` separate.
    assert st.scoped_field_offsets() == {
        "A.x": 0,
        "A.b": 1,
        "B.x": 0,
        "B.y": 1,
    }
    # Field types resolve nesting (A.b → B for ``a->b->y``).
    assert st.field_types() == {"A.x": "unsigned int", "A.b": "B", "B.x": "unsigned int", "B.y": "unsigned int"}
