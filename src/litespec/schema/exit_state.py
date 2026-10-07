"""Exit-state records (§3)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import ExitTargetKind
from litespec.schema.primitives import Identifier, LabelPath, LIRNodeRef, NodeId, Predicate


class ProvenanceMap(LiteSpecModel):
    """§3 ``ProvenanceMap ::= { node_map, hash }``."""

    node_map: dict[Identifier, LIRNodeRef] = {}
    hash: str


class ExitStateModel(LiteSpecModel):
    """§3 ``ExitStateModel``."""

    enabled: bool
    return_targets: list[LabelPath] = []
    break_targets: list[LabelPath] = []
    continue_targets: list[LabelPath] = []
    provenance_map: Optional[ProvenanceMap] = None


class ExitDisjunct(LiteSpecModel):
    """§3 ``ExitDisjunct``."""

    label: LabelPath = []
    target_kind: ExitTargetKind
    target_loop: Optional[Identifier] = None
    condition: Predicate
    post: Predicate
    path_ref: Optional[NodeId] = None


class ExitState(LiteSpecModel):
    """§3 ``ExitState ::= { disjuncts }``."""

    disjuncts: list[ExitDisjunct] = []
