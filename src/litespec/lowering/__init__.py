"""LIR→Rust lowering (Phase 4)."""

from litespec.lowering.effect_expr_to_rust import RustEmitter, render_effect_rust, render_expr_rust
from litespec.lowering.port_module import emit_baremetal, port_module
from litespec.lowering.rust_source_writer import write_rust_source
from litespec.lowering.rust_type_mapping import rust_default, rust_type
from litespec.lowering.safe_api_emitter import emit_safe_api
from litespec.lowering.unsafe_core_emitter import emit_function, emit_module

__all__ = [
    "RustEmitter",
    "emit_baremetal",
    "emit_function",
    "emit_module",
    "emit_safe_api",
    "port_module",
    "render_effect_rust",
    "render_expr_rust",
    "rust_default",
    "rust_type",
    "write_rust_source",
]
