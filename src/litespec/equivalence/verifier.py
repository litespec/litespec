"""End-to-end formal verification of a single C function (Phase 8)."""

from __future__ import annotations

from litespec.equivalence.layered_ec import run_layered_ec
from litespec.type_mapping import TypeModel, default_type_model


def verify_function(c_source: str | bytes, name: str, type_model: TypeModel | None = None, config=None):
    """Extract → lower → emit ISIR → run the layered equivalence chain.

    Returns ``(CheckResult, RefinementChain)`` where each seam now performs a
    concrete check (LIR non-trivial, Rust compiles, ISIR validates, safe wrapper).
    """
    from litespec.extraction import attach_contract, extract_function
    from litespec.extraction.type_modeling import c_param_to_type_expr, c_return_to_type_expr
    from litespec.interscope.isir import emit_isir_module
    from litespec.lowering import emit_safe_api, port_module
    from litespec.lowering.rust_type_mapping import set_type_model

    tm = type_model or default_type_model()
    set_type_model(tm)
    fn = extract_function(c_source, name, type_model=tm, config=config)
    params = [(n, c_param_to_type_expr(t, n, type_model=tm)) for n, t in fn.parameters]
    ret = c_return_to_type_expr(fn.return_type, type_model=tm)
    # port_module handles file-scope globals (g_poolHead, g_vmBootMemBase, …) so the
    # emitted Rust compiles even for functions that read/write globals.
    rust = port_module(c_source, [name], type_model=tm, config=config)
    safe = emit_safe_api(name, params, ret)
    contract = attach_contract(c_source, name)
    if not contract.postconditions and not contract.preconditions:
        # No ACSL annotation in the C source → synthesize a default postcondition
        # so the ISIR carries a proof obligation for InterScope to discharge.
        from litespec.extraction.contract_attachment import synthesize_contract

        contract = synthesize_contract(fn.return_type, name)
    isir = emit_isir_module(name, fn.state_vars, fn.effect, contract, params=params)

    return run_layered_ec(c_source=c_source, lir=fn, rust=rust, unsafe=rust, safe=safe, isir=isir)
