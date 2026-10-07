"""``conformance`` command: run the §2 criteria surface (Phase 9)."""

from __future__ import annotations

from litespec.serialization import load_litespec
from litespec.validation import CONFORMANCE_CRITERIA, check_conformance, check_placeholders


def conformance_command(argv: list[str]) -> int:
    path = argv[0] if argv else "examples/mm_search_typed_binder/mm_search_typed_binder.litespec.yaml"
    doc = load_litespec(path)

    report = check_conformance(doc)
    placeholders = check_placeholders(doc)

    print(f"conformance: {path}")
    print(f"  criteria: 1–{len(CONFORMANCE_CRITERIA)} declared; structural checks via well-formedness")
    print(f"  well-formedness: {'OK' if report.ok else 'VIOLATIONS'}")
    print(f"  placeholders: {'OK' if placeholders.ok else 'VIOLATIONS'}")

    ok = report.ok and placeholders.ok
    if not report.ok:
        for line in report.failures:
            print("  " + line)
    if not placeholders.ok:
        for err in placeholders.errors:
            print("  " + err)
    return 0 if ok else 1
