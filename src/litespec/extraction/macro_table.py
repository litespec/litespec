"""Macro table: extract ``#define`` directives from a translation unit (Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from tree_sitter import Node

from litespec.extraction.expression_mapping import _text


@dataclass
class MacroTable:
    """Object-like and function-like macros defined in a translation unit."""

    constants: dict[str, str] = field(default_factory=dict)  # name → value text
    functions: dict[str, tuple[tuple[str, ...], str]] = field(default_factory=dict)  # name → (params, body)

    @classmethod
    def from_translation_unit(cls, tu: Node) -> MacroTable:
        constants: dict[str, str] = {}
        functions: dict[str, tuple[tuple[str, ...], str]] = {}

        def walk(node: Node) -> None:
            if node.type == "preproc_def":
                name = node.child_by_field_name("name")
                value = node.child_by_field_name("value")
                if name is not None and value is not None:
                    # First definition wins: board/config headers define a macro
                    # (e.g. ``LOSCFG_BASE_CORE_TICK_PER_SECOND``) before the guarded
                    # ``#ifndef … #define … default`` fallback in later headers, and
                    # the guarded redefinition must not clobber it.
                    constants.setdefault(_text(name), _text(value).strip())
            elif node.type == "preproc_function_def":
                name = node.child_by_field_name("name")
                params = node.child_by_field_name("parameters")
                value = node.child_by_field_name("value")
                if name is not None and value is not None:
                    ptext = _text(params) if params is not None else ""
                    vtext = _text(value).strip()
                    # GNU/C99 variadic macros (``args...``, ``__VA_ARGS__``, ``##``
                    # token-paste) cannot be expanded faithfully by the simple
                    # parameter-substitution pass; leave their calls intact so the
                    # lowering emits a variadic stub / macro_rules! no-op instead.
                    variadic = "..." in ptext or "##" in vtext or "__VA_ARGS__" in vtext
                    if not variadic:
                        pnames = tuple(p.strip() for p in ptext.strip("()").split(",") if p.strip())
                        functions[_text(name)] = (pnames, vtext)
            elif node.type == "enum_specifier":
                # Collect enum members as integer constants so array sizes and
                # expressions can resolve them (e.g. ``arr[OS_QUEUE_N_RW]``).
                body = next((c for c in node.named_children if c.type == "enumerator_list"), None)
                if body is not None:
                    running = 0
                    for enc in body.named_children:
                        if enc.type != "enumerator":
                            continue
                        name = enc.child_by_field_name("name")
                        if name is None:
                            continue
                        value = enc.child_by_field_name("value")
                        if value is not None:
                            vtext = _text(value)
                            try:
                                running = int(vtext, 0)
                            except ValueError:
                                # ``A = B`` — reference to an earlier enum member / macro.
                                if vtext in constants:
                                    try:
                                        running = int(constants[vtext], 0)
                                    except ValueError:
                                        running += 1
                                else:
                                    running += 1
                        constants[_text(name)] = str(running)
                        running += 1
            for child in node.named_children:
                walk(child)

        walk(tu)
        return cls(constants=constants, functions=functions)

    def is_empty(self) -> bool:
        return not self.constants and not self.functions
