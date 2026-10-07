"""Multi-function porting: emit several C functions into one Rust module (Phase 4)."""

from __future__ import annotations

import re

from litespec.extraction import extract_function
from litespec.extraction.global_table import GlobalTable
from litespec.extraction.struct_table import StructTable
from litespec.extraction.type_modeling import c_param_to_type_expr, c_return_to_type_expr
from litespec.intrinsics import INTRINSICS, register_mmio_from_target
from litespec.lowering.effect_expr_to_rust import (
    assigned_targets,
    memory_model,
    reset_addr_slots,
    set_call_fn_ptr,
    set_casts,
    set_embedded_fields,
    set_field_elem_sizes,
    set_field_offsets,
    set_field_types,
    set_globals,
    set_scoped_field_offsets,
    set_union_members,
    set_var_struct_types,
    set_variadic,
)
from litespec.lowering.goto_elimination import eliminate_gotos
from litespec.lowering.rust_type_mapping import int_type, set_type_model
from litespec.lowering.stub_scaffold import collect_external_symbols, render_stub_scaffold
from litespec.lowering.unsafe_core_emitter import emit_function
from litespec.type_mapping import TypeModel, default_type_model


def port_module(
    c_source: str | bytes,
    function_names: list[str],
    type_model: TypeModel | None = None,
    config=None,
    executable: bool = False,
    module_name: str = "",
    mock_returns: dict[str, int] | None = None,
) -> str:
    """Port several C functions into a single self-contained Rust module (host-sim).

    Cross-references between the ported functions become real calls; only the
    functions that are *not* ported (plus memory/field access) remain stubs.

    ``module_name`` (e.g. the target's ``port_name``) wraps the emitted code in
    ``pub mod <name> { … }`` so the ported artifact has a stable crate/module name.
    ``mock_returns`` overrides specific stub return values (mock allocator addresses).
    """
    return _port_module(
        c_source,
        function_names,
        type_model=type_model,
        config=config,
        executable=executable,
        module_name=module_name,
        baremetal=False,
        target=None,
        mock_returns=mock_returns,
    )


def emit_baremetal(
    c_source: str | bytes,
    function_names: list[str],
    target,
    type_model: TypeModel | None = None,
    config=None,
) -> str:
    """Port C functions into a bootable ``#![no_std]`` bare-metal crate.

    Emits the volatile memory model, ``global_asm!`` for the target's arch
    ``.S`` files, a ``#[panic_handler]``, and a ``rmain`` entry that prints via the
    target's UART stub. The arch/linker/uart/triple come from ``target``
    (``TargetRequirements``, read from ``config/targets/*.yaml``) — the emitter is
    generic, the board support lives in ``targets/<port_name>/``.
    """
    return _port_module(
        c_source,
        function_names,
        type_model=type_model,
        config=config,
        executable=False,
        module_name="",
        baremetal=True,
        target=target,
    )


def _port_module(
    c_source: str | bytes,
    function_names: list[str],
    type_model: TypeModel | None = None,
    config=None,
    executable: bool = False,
    module_name: str = "",
    baremetal: bool = False,
    target=None,
    mock_returns: dict[str, int] | None = None,
) -> str:
    tm = type_model or default_type_model()
    set_type_model(tm)
    # Intrinsics (CPU-register accessors, builtins, …) are rendered inline, not
    # ported as functions — e.g. ArchCurrTaskGet/Set become the current-task cell.
    function_names = [n for n in function_names if n not in INTRINSICS]
    ported = set(function_names)
    fns: list[tuple] = []
    for name in function_names:
        fn = extract_function(c_source, name, type_model=tm, config=config)
        params = [(n, c_param_to_type_expr(t, n, type_model=tm)) for n, t in fn.parameters]
        ret = c_return_to_type_expr(fn.return_type, type_model=tm)
        fns.append((fn, params, ret))

    from litespec.extraction import parse_c

    # Globals: file-scope declarations plus any assigned name that is not a param/local
    # (e.g. extern globals like g_vmBootMemBase that are assigned in some function).
    all_assigned: set[str] = set()
    all_declared: set[str] = set()
    for fn, params, ret in fns:
        all_assigned |= assigned_targets(fn.effect)
        all_declared |= {n for n, _ in params} | {n for n, _ in fn.state_vars}
    globals_ = GlobalTable.from_translation_unit(parse_c(c_source)).names | {
        n for n in (all_assigned - all_declared) if re.fullmatch(r"[A-Za-z_]\w*", n)
    }
    struct_table = StructTable.from_translation_unit(parse_c(c_source))
    field_offsets = struct_table.field_offsets()
    scoped_field_offsets = struct_table.scoped_field_offsets()
    field_types = struct_table.field_types()
    embedded_fields = struct_table.embedded_fields()

    # Variable → struct type name (from params/locals), so field offsets resolve
    # per-struct instead of by a globally-colliding field name.
    var_struct_types: dict[str, str] = {}
    for fn, params, ret in fns:
        for n, t in params:
            if t in struct_table.structs:
                var_struct_types[n] = t
        for n, t in fn.state_vars:
            if t in struct_table.structs:
                var_struct_types[n] = t

    unknown_types: set[str] = set()
    functions: dict[str, tuple[int, str, bool]] = {}
    arity_sets: dict[str, set[int]] = {}
    per_fn_variadic: set[str] = set()
    constants: set[str] = set()
    fn_ptrs: set[str] = set()
    for fn, params, ret in fns:
        effect = eliminate_gotos(fn.effect)
        ut, fc, cn, fnp = collect_external_symbols(effect, params, fn.state_vars, ret)
        unknown_types |= ut
        constants |= cn
        fn_ptrs |= fnp
        for fname, (arity, rt, variadic) in fc.items():
            if fname in ported or fname in globals_:
                continue  # a ported function / global is not a stub
            arity_sets.setdefault(fname, set()).add(arity)
            if variadic:
                per_fn_variadic.add(fname)
            prev = functions.get(fname)
            if prev is None:
                functions[fname] = (arity, rt, False)
            else:
                functions[fname] = (max(prev[0], arity), prev[1], False)

    # Function-pointer variables / weak symbols are globals, not function stubs.
    for name in fn_ptrs:
        functions.pop(name, None)
        globals_.add(name)

    # Function-pointer params/locals (declared AND called, e.g. ``checkFunc(...)``)
    # render through ``__call_fn_ptr__``, not a function stub.
    call_fn_ptrs = set(functions) & all_declared
    for name in call_fn_ptrs:
        functions.pop(name, None)
    set_call_fn_ptr(call_fn_ptrs)

    # Variadic if any single function saw multiple arities, or arities differ across functions.
    for fname in list(functions):
        n_args, rt, _ = functions[fname]
        functions[fname] = (n_args, rt, (fname in per_fn_variadic) or len(arity_sets[fname]) > 1)

    # Globals are statics, not const stubs; names declared (param/local) in *any*
    # function are not constants either (e.g. ``intSave`` is a param in some
    # functions and a local in others).
    constants -= globals_
    constants -= all_declared
    # A ported function referenced as a value (``TSK_ENTRY_FUNC(OsIdleTask)``) is a
    # function pointer, not a missing constant; don't emit a shadowing const stub.
    constants -= ported

    # Executable mode: memset/memset_s become real memory-clears, not stubs.
    if executable:
        for mem_fn in ("memset", "memset_s"):
            functions.pop(mem_fn, None)

    # Type casts (``UINT64(x)`` → ``(x as u64)``) and intrinsics (``CLZ``/``PRINTK``)
    # are rendered inline by ``render_expr_rust``, not via function stubs; stubbing
    # them would be dead code and can collide with a same-named type alias.
    for name in set(tm.c_to_lir) | set(INTRINSICS):
        functions.pop(name, None)

    scaffold = render_stub_scaffold(
        unknown_types, functions, constants, executable=executable, mock_returns=mock_returns
    )
    set_variadic({n for n, (_, _, v) in functions.items() if v})
    set_globals(globals_)
    set_field_offsets(field_offsets)
    set_scoped_field_offsets(scoped_field_offsets)
    set_var_struct_types(var_struct_types)
    set_field_types(field_types)
    set_embedded_fields(embedded_fields)
    set_field_elem_sizes(struct_table.field_elem_sizes())
    set_union_members(struct_table.union_members)
    reset_addr_slots()
    set_casts({name: tm.lir_to_rust_type(tm.c_to_lir[name]) for name in tm.c_to_lir})
    register_mmio_from_target()
    parts = [
        "// generated by litespec (Phase 4 lowering — multi-function)",
        "#![allow(dead_code)]",
        "#![allow(unused_assignments)]",
        "#![allow(unused_variables)]",
        "#![allow(unused_mut)]",
        "#![allow(unused_parens)]",
        "#![allow(non_snake_case)]",
        "#![allow(clippy::all)]",
        "#![allow(arithmetic_overflow)]",  # C unsigned arithmetic wraps
        "#![allow(static_mut_refs)]",  # globals are static mut
    ]
    if baremetal:
        parts[1:1] = [
            "#![no_std]",
            "#![no_main]",
        ]
        # `use` must follow the inner attributes (they all annotate the crate root).
        parts.append("use core::panic::PanicInfo;")
    parts.append("// flat word-addressable memory model" if not baremetal else "// bare-metal volatile memory model")
    it = int_type()
    parts.append(memory_model(it, executable=executable, baremetal=baremetal))
    if scaffold:
        parts.append("// stubs for external symbols (unported helpers)")
        parts.append(scaffold)
    if globals_:
        parts.append("// file-scope globals")
        parts.append("\n".join(f"static mut {g}: {it} = 0;" for g in sorted(globals_)))
        parts.append(f"unsafe fn __call_fn_ptr__(_f: {it}) -> {it} {{ unimplemented!() }}")
    for fn, params, ret in fns:
        parts.append(emit_function(fn.name, params, ret, fn.state_vars, fn.effect, unsafe=True))
    if baremetal:
        parts.append(_baremetal_scaffold(target))
    body = "\n\n".join(parts) + "\n"
    if module_name:
        # Indent the crate body and wrap it in `pub mod <name> { … }`.
        indented = "\n".join(("    " + line) if line.strip() else line for line in body.split("\n"))
        return f"pub mod {module_name} {{\n{indented}\n}}\n"
    return body


def _baremetal_scaffold(target) -> str:
    """Emit the ``#![no_std]`` boot scaffolding (panic handler, UART, entry).

    The arch ``.S`` files are assembled separately and linked (their GAS register
    lists use ``{…}``, which ``global_asm!`` would treat as format placeholders).
    """
    uart = f'include!("{target.uart_stub}");' if target.uart_stub else "// no UART stub declared"
    return (
        f"// arch assembly assembled separately and linked: {', '.join(target.asm_files)}\n"
        f"#[panic_handler]\n"
        f"fn panic(_info: &PanicInfo) -> ! {{ loop {{}} }}\n\n"
        f"// UART stub (MMIO, target-provided)\n"
        f"{uart}\n\n"
        f"// entry point (called by the reset vector)\n"
        f"#[no_mangle]\n"
        f'pub extern "C" fn rmain() -> ! {{\n'
        f'    unsafe {{ uart_puts("hello from rliteos\\n"); }}\n'
        f"    loop {{}}\n"
        f"}}"
    )
