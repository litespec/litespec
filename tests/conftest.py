from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture(scope="session")
def mm_search_typed_binder_path() -> Path:
    p = EXAMPLES_DIR / "mm_search_typed_binder" / "mm_search_typed_binder.litespec.yaml"
    assert p.exists(), f"example missing: {p}"
    return p


@pytest.fixture(autouse=True)
def reset_type_model():
    from litespec.lowering.effect_expr_to_rust import reset_addr_slots, set_addr_taken
    from litespec.lowering.rust_type_mapping import set_type_model
    from litespec.type_mapping import default_type_model

    set_type_model(default_type_model())
    reset_addr_slots()
    set_addr_taken({})
    yield
