"""type-expression parser (§7.2)."""

from litespec.schema.type_expressions import parse_type_expr


def test_primitive():
    t = parse_type_expr("Nat")
    assert t.kind == "primitive" and t.name == "Nat"


def test_identifier():
    t = parse_type_expr("Block")
    assert t.kind == "identifier" and t.name == "Block"


def test_list():
    t = parse_type_expr("List<Block>")
    assert t.kind == "list"
    assert t.element.kind == "identifier"
    assert t.element.name == "Block"


def test_map():
    t = parse_type_expr("Map<Nat, Block>")
    assert t.kind == "map"
    assert t.key.name == "Nat"
    assert t.value.name == "Block"


def test_record():
    t = parse_type_expr("{ offset : Nat, size : Nat }")
    assert t.kind == "record"
    assert set(t.fields) == {"offset", "size"}
