"""Path-condition DAG and PathDagOp records (§3, §9.22)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import PathNodeKind
from litespec.schema.primitives import Identifier, NodeId, Predicate, SymbolicVar


class PathNode(LiteSpecModel):
    """§3 ``PathNode``."""

    node_id: NodeId
    indicator: SymbolicVar
    parent: Optional[NodeId] = None
    guard: Predicate
    kind: PathNodeKind


class PathConditionDAG(LiteSpecModel):
    """§3 ``PathConditionDAG ::= { dag_id, nodes, root }``."""

    dag_id: Identifier
    nodes: list[PathNode] = []
    root: NodeId


class PathDagOp(LiteSpecModel):
    """§3 ``PathDagOp``."""

    dag_id: Identifier
    root: NodeId
    indicator_naming: str
    canonical_hash: str
    derived_smt2_hash: str
    nodes: list[PathNode] = []


class PathDAGSerialization(LiteSpecModel):
    """§3 ``PathDAGSerialization``."""

    representation: str = "dag"
    dag_serialization: str  # "inline" | "embedded" | "external"
    external_format: Optional[str] = None


class PathDAGArtifact(LiteSpecModel):
    """§3 ``PathDAGArtifact``."""

    canonical_format: str = "smt-lib2"
    smt2_form_hash: str
    clause_order: str = "topological_parent_before_child"
    indicator_naming: str
    file_uri: Optional[str] = None


class InlineAxiomStream(LiteSpecModel):
    """§3 ``InlineAxiomStream``."""

    kind: str = "inline"
    axioms: list[str] = []
    smt2_form_hash: str
    indicator_naming: str
