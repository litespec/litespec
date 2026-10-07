"""InterScope integration (Phase 7)."""

from litespec.interscope.client import run_interscope
from litespec.interscope.isir import emit_isir_module, validate_isir
from litespec.interscope.results import parse_proof_result

__all__ = ["emit_isir_module", "parse_proof_result", "run_interscope", "validate_isir"]
