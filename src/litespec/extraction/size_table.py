"""C type size table (Phase 2).

The port's memory model is *word-addressable* (``MEM[word]``, one word per field), so
``sizeof`` returns **word counts**, not bytes: every primitive/pointer is 1 word, and
a struct is the sum of its fields' word counts. This keeps ``sizeof`` consistent with
the word-indexed field offsets used by the memory model.
"""

from __future__ import annotations

from litespec.extraction.struct_table import StructTable

_POINTER_WORDS = 1

_PRIMITIVE_SIZES: dict[str, int] = {
    "void": 1,
    "VOID": 1,
    "char": 1,
    "CHAR": 1,
    "unsigned char": 1,
    "UINT8": 1,
    "INT8": 1,
    "UCHAR": 1,
    "short": 1,
    "SHORT": 1,
    "unsigned short": 1,
    "UINT16": 1,
    "INT16": 1,
    "USHORT": 1,
    "int": 1,
    "INT": 1,
    "unsigned int": 1,
    "UINT": 1,
    "UINT32": 1,
    "INT32": 1,
    "BOOL": 1,
    "long": 1,
    "LONG": 1,
    "unsigned long": 1,
    "ULONG": 1,
    "long long": 1,
    "unsigned long long": 1,
    "UINT64": 1,
    "INT64": 1,
    "INTPTR": 1,
    "UINTPTR": 1,
    "SIZE_T": 1,
    "SSIZE_T": 1,
}


def compute_sizes(struct_table: StructTable) -> dict[str, int]:
    """Type name → word count (1 per field, recursively for nested structs).

    Iterates to a fixpoint so structs may reference structs defined later in the
    translation unit (forward references).
    """
    sizes: dict[str, int] = dict(_PRIMITIVE_SIZES)
    for _ in range(len(struct_table.structs) + 1):
        changed = False
        for sname, fields in struct_table.structs.items():
            total = 0
            for f in fields:
                if f.is_pointer:
                    elem = _POINTER_WORDS  # a pointer is one word, regardless of pointed-to size
                else:
                    base = f.base_type.replace("struct ", "").replace("enum ", "").replace("union ", "").strip()
                    elem = sizes.get(base, _POINTER_WORDS)
                total += (f.array_size or 1) * elem
            if sizes.get(sname) != total:
                sizes[sname] = total
                changed = True
        if not changed:
            break
    return sizes


def sizeof_type(type_text: str, sizes: dict[str, int]) -> int:
    """Word count of a ``sizeof`` argument (``struct X``, ``T``, or ``T *``)."""
    t = type_text.replace("struct ", "").replace("enum ", "").replace("union ", "").strip()
    if "*" in t or t in ("void", "VOID"):
        return _POINTER_WORDS
    return sizes.get(t, _POINTER_WORDS)
