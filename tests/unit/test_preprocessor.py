"""Preprocessor + recursive function discovery tests."""

from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.preprocessor import preprocess_c


def test_preprocess_c_removes_inactive_branches():
    src = "#define FOO 1\n#if FOO\nint active(void) { return 1; }\n#else\nint inactive(void) { return 0; }\n#endif\n"
    out = preprocess_c(src, {})
    assert "active" in out
    assert "inactive" not in out


def test_preprocess_c_applies_defines():
    src = "#if FLAG\nint yes(void) { return 1; }\n#endif\n"
    out = preprocess_c(src, {"FLAG": 1})
    assert "yes" in out


def test_recursive_functions_finds_ifdef_wrapped():
    src = b"#ifdef A\nint wrapped(void) { return 1; }\n#endif\nint top(void) { return 0; }\n"
    tu = parse_c(src)
    names = {f.name for f in functions(tu)}
    assert "wrapped" in names and "top" in names
