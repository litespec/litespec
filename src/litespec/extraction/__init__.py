"""C→LIR extraction (Phase 2)."""

from litespec.extraction.acsl_parser import AcslClause, is_acsl_comment, parse_acsl
from litespec.extraction.c_parser import parse_c, parse_c_file
from litespec.extraction.c_to_lir import ExtractedFunction, extract_function
from litespec.extraction.c_translation_unit import CFunction, find_function, functions
from litespec.extraction.contract_attachment import attach_contract
from litespec.extraction.loop_analysis_extraction import collect_loop_analyses
from litespec.extraction.statement_mapping import map_function_body, map_statement
from litespec.extraction.translation_validator import validate_translation

__all__ = [
    "AcslClause",
    "CFunction",
    "ExtractedFunction",
    "attach_contract",
    "collect_loop_analyses",
    "extract_function",
    "find_function",
    "functions",
    "is_acsl_comment",
    "map_function_body",
    "map_statement",
    "parse_acsl",
    "parse_c",
    "parse_c_file",
    "validate_translation",
]
