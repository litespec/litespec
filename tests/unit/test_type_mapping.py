"""Type-model configuration: C ↔ LIR ↔ ISIR ↔ Rust mappings."""

from litespec.extraction.type_modeling import c_param_to_type_expr, c_return_to_type_expr
from litespec.type_mapping import default_type_model, load_type_model


def test_c_type_to_lir():
    tm = default_type_model()
    assert tm.c_type_to_lir("unsigned int") == "Nat"
    assert tm.c_type_to_lir("size_t") == "Nat"
    assert tm.c_type_to_lir("int") == "Int"
    assert tm.c_type_to_lir("bool") == "Bool"
    assert tm.c_type_to_lir("float") == "Rat"
    assert tm.c_type_to_lir("void") == "Unit"
    assert tm.c_type_to_lir("void", pointer=True) == "Nat"  # void* → opaque handle
    assert tm.c_type_to_lir("Block") == "Block"  # user type falls through


def test_lir_to_isir():
    tm = default_type_model()
    assert tm.lir_to_isir_type("Nat") == "bits<32>"
    assert tm.lir_to_isir_type("Bool") == "bool"
    assert tm.lir_to_isir_type("Block") == "bits<32>"  # default width


def test_lir_to_rust():
    tm = default_type_model()
    assert tm.lir_to_rust_type("Nat") == "u64"
    assert tm.lir_to_rust_type("Block") == "Block"


def test_param_type_expr():
    assert c_param_to_type_expr("unsigned int size", "size") == "Nat"
    assert c_param_to_type_expr("void *pool", "pool") == "Nat"


def test_return_type_expr():
    assert c_return_to_type_expr("void *") == "Nat"
    assert c_return_to_type_expr("unsigned int") == "Nat"


def test_load_type_model():
    tm = load_type_model("default")
    assert tm.name == "default"


def test_liteos_type_model_extends_default():
    tm = load_type_model("liteos")
    # LiteOS typedefs.
    assert tm.c_type_to_lir("UINT32") == "Nat"
    assert tm.c_type_to_lir("INT32") == "Int"
    assert tm.c_type_to_lir("VOID") == "Unit"
    assert tm.c_type_to_lir("VOID", pointer=True) == "Nat"  # VOID* → opaque handle
    assert tm.c_type_to_lir("BOOL") == "Int"
    # 64-bit types map to the 32-bit word (the memory model is 32-bit word-addressable).
    assert tm.c_type_to_lir("UINT64") == "Nat"
    assert tm.c_type_to_lir("INT64") == "Int"
    assert tm.lir_to_rust_type("Nat64") == "u64"  # Nat64 still exists in the default model
    assert tm.lir_to_rust_type("Nat") == "u32"
    assert tm.word_bits == 32
    assert tm.word_type() == "u32"
    assert load_type_model("default").word_type() == "u64"
    # Inherited from the default model.
    assert tm.c_type_to_lir("unsigned int") == "Nat"
    assert tm.c_type_to_lir("int") == "Int"


def test_word_width_abstraction_drives_memory_model():
    from litespec.lowering.rust_type_mapping import int_type, set_type_model

    # 32-bit target (LiteOS): word → u32.
    tm32 = load_type_model("liteos")
    set_type_model(tm32)
    assert int_type() == tm32.word_type() == "u32"

    # 64-bit target (default): word → u64.
    tm64 = default_type_model()
    set_type_model(tm64)
    assert int_type() == tm64.word_type() == "u64"
