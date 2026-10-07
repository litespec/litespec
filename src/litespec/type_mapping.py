"""Type-model configuration: C ↔ LIR ↔ ISIR ↔ Rust type mappings.

Loads a type model from ``config/type-models/<name>.yaml``. This removes
target-specific type/width assumptions from the core pipeline; specialized
targets add their own type model and reference it from their requirements config.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class TypeModel:
    name: str
    c_void_pointer: str = "Nat"
    c_void_names: set[str] = field(default_factory=lambda: {"void"})
    word_bits: int = 64
    lir_to_isir_default: str = "bits<32>"
    lir_to_rust_default: str = ""
    c_to_lir: dict[str, str] = field(default_factory=dict)
    lir_to_isir: dict[str, str] = field(default_factory=dict)
    lir_to_rust: dict[str, str] = field(default_factory=dict)
    #: C typedef name → underlying C type text (for the reference-C preamble).
    c_typedefs: dict[str, str] = field(default_factory=dict)

    def c_type_to_lir(self, c_text: str, *, pointer: bool = False) -> str:
        """Map a C type text to a LIR ``TypeExpr`` (pointer → index lowering)."""
        t = " ".join(c_text.split()).replace("*", "").strip()
        # strip decl/storage qualifiers and aggregate keywords in any order
        while True:
            stripped = False
            for kw in (
                "struct ",
                "enum ",
                "union ",
                "const ",
                "volatile ",
                "static ",
                "inline ",
                "extern ",
                "STATIC ",
                "INLINE ",
                "EXTERN ",
            ):
                if t.startswith(kw):
                    t = t[len(kw) :].strip()
                    stripped = True
            if not stripped:
                break
        if t in self.c_void_names and pointer:
            return self.c_void_pointer
        # Strip empty section/attribute macros (``LITE_OS_SEC_*``, ``WEAK``, …) that
        # decorate function signatures but are not part of the type.
        t = re.sub(r"\b(?:LITE_OS_SEC_\w+|WEAK|USED|NORETURN|DEPRECATED)\b", "", t).strip()
        return self.c_to_lir.get(t, t)  # user identifiers fall through as-is

    def lir_to_isir_type(self, lir_type: str) -> str:
        return self.lir_to_isir.get(lir_type, self.lir_to_isir_default)

    def lir_to_rust_type(self, lir_type: str) -> str:
        return self.lir_to_rust.get(lir_type, self.lir_to_rust_default or lir_type)

    def word_type(self) -> str:
        """The fixed-width Rust word type for this target (``u32`` / ``u64``)."""
        return f"u{self.word_bits}"


def type_model_dir() -> Path:
    return _PROJECT_ROOT / "config" / "type-models"


def load_type_model(name: str = "default") -> TypeModel:
    """Load a type model from ``config/type-models/<name>.yaml``.

    A model may declare ``extends: <parent>``; the parent's mappings are merged
    and overridden by the child's.
    """
    path = type_model_dir() / f"{name}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    parent: TypeModel | None = None
    parent_name = data.get("extends")
    if parent_name:
        parent = load_type_model(parent_name)

    def pick(key: str, fallback):
        if parent is None:
            return data.get(key, fallback)
        return _merge(getattr(parent, key), data.get(key, {}))

    return TypeModel(
        name=data.get("name", name),
        c_void_pointer=data.get("c_void_pointer", parent.c_void_pointer if parent else "Nat"),
        c_void_names=set(data.get("c_void_names", parent.c_void_names if parent else {"void"})),
        word_bits=int(data.get("word_bits", parent.word_bits if parent else 64)),
        lir_to_isir_default=data.get("lir_to_isir_default", parent.lir_to_isir_default if parent else "bits<32>"),
        lir_to_rust_default=data.get("lir_to_rust_default", parent.lir_to_rust_default if parent else ""),
        c_to_lir=pick("c_to_lir", {}),
        lir_to_isir=pick("lir_to_isir", {}),
        lir_to_rust=pick("lir_to_rust", {}),
        c_typedefs=pick("c_typedefs", {}),
    )


def _merge(parent: dict, child: dict) -> dict:
    out = dict(parent)
    out.update(child)
    return out


def default_type_model() -> TypeModel:
    return load_type_model("default")
