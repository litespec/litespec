"""Reproducibility records (§17). Phase 1 placeholder."""

from __future__ import annotations

from pydantic import ConfigDict

from litespec.schema.base import LiteSpecModel


class PipelineReproducibility(LiteSpecModel):
    """§17.16 ``PipelineReproducibility`` (permissive placeholder)."""

    model_config = ConfigDict(extra="allow")
