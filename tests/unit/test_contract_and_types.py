"""ACSL contract attachment, D85 type declarations, translation validation."""

from litespec.derivation import derive_type_declarations
from litespec.extraction import attach_contract, extract_function, parse_acsl, validate_translation

_C_SOURCE = """\
/*@ requires size > 0;
    ensures result != 0; */
void *LOS_MemAlloc(void *pool, unsigned int size) {
    void *result = 0;
    Block *cursor = (Block *)pool;
    /*@ loop invariant cursor != 0; */
    while (cursor->size < size) {
        cursor = cursor->next;
    }
    return result;
}
"""


def test_parse_acsl():
    clauses = parse_acsl("/*@ requires size > 0; ensures result != 0; */")
    assert [(c.kind, c.expression) for c in clauses] == [
        ("requires", "size > 0"),
        ("ensures", "result != 0"),
    ]


def test_attach_contract():
    contract = attach_contract(_C_SOURCE, "LOS_MemAlloc")
    assert [p.expression for p in contract.preconditions] == ["size > 0"]
    assert [p.expression for p in contract.postconditions] == ["result != 0"]
    assert contract.loop_invariants is not None
    assert [li.expr for li in contract.loop_invariants] == ["cursor != 0"]


def test_derive_type_declarations():
    fn = extract_function(_C_SOURCE, "LOS_MemAlloc")
    decls = derive_type_declarations(fn.state_vars)
    assert [d.name for d in decls] == ["Block"]


def test_translation_validator():
    fn = extract_function(_C_SOURCE, "LOS_MemAlloc")
    assert validate_translation(fn) == []
