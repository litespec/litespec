"""Rust verification backends (Phase 6)."""

from litespec.backends.backend_protocol import Backend, is_trivial_obligation
from litespec.backends.backend_registry import all_backends, backend_names, get_backend
from litespec.backends.dispatch_table import dispatch

__all__ = [
    "Backend",
    "all_backends",
    "backend_names",
    "dispatch",
    "get_backend",
    "is_trivial_obligation",
]
