"""Base Pydantic model shared by all LiteSpec schema records."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LiteSpecModel(BaseModel):
    """Base model.

    ``extra="forbid"`` turns Pydantic into a schema validator: unknown keys are
    rejected, enforcing the spec's mandatory/optional field discipline. Optional
    fields default to ``None`` (the spec's ``⊥``) and are omitted on dump.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
