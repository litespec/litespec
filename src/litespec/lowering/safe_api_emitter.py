"""Safe-API Rust emission (Phase 4): ``Result``-wrapped wrapper over the unsafe core."""

from __future__ import annotations

from litespec.lowering.rust_type_mapping import rust_type


def emit_safe_api(
    name: str,
    params: list[tuple[str, str]],
    return_type: str,
) -> str:
    """Emit a safe ``Result``-returning wrapper that delegates to the unsafe core."""
    param_str = ", ".join(f"{n}: {rust_type(t)}" for n, t in params)
    args = ", ".join(n for n, _ in params)
    rt = rust_type(return_type)
    return f"pub fn {name}_safe({param_str}) -> Result<{rt}, ()> {{\n    Ok(unsafe {{ {name}_unsafe({args}) }})\n}}\n"
