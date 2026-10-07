"""Leaf records and type aliases shared across the LiteSpec wire format."""

from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import Field

from litespec.schema.base import LiteSpecModel

# --------------------------------------------------------------------------- #
# type aliases
# --------------------------------------------------------------------------- #

Identifier = str
SpecId = str
SemVer = str
NodeId = str
SymbolicVar = str
LabelPath = list[str]
Value = Union[bool, int, str, float, list["Value"], dict[str, "Value"]]
Bound = Union[int, Literal["unbounded"]]


# --------------------------------------------------------------------------- #
# §3 / §6 predicate and artifact records
# --------------------------------------------------------------------------- #


class Predicate(LiteSpecModel):
    """§6.1 ``Predicate ::= { expression, description, formal_lang?, name? }``."""

    expression: str
    description: str
    formal_lang: Optional[str] = None
    name: Optional[Identifier] = None


class WitnessArtifact(LiteSpecModel):
    """§3 ``WitnessArtifact ::= { kind, uri, hash }``."""

    kind: Literal["proof", "counterexample", "trace", "report"]
    uri: str
    hash: str


class LIRNodeRef(LiteSpecModel):
    """§7.5 ``LIRNodeRef ::= { function, node_id }``."""

    function: Identifier
    node_id: Identifier


class ConfigExpr(LiteSpecModel):
    """§7.1 ``ConfigExpr ::= { arithmetic_class, expression }``."""

    arithmetic_class: Literal["linear", "nonlinear"]
    expression: str


IntOrConfig = Union[int, ConfigExpr]


# --------------------------------------------------------------------------- #
# §3 hash bindings and grammar imports
# --------------------------------------------------------------------------- #


class HashBinding(LiteSpecModel):
    """§3 ``HashBinding ::= { field, value?, symbolic_ref?, notes? }``."""

    field: str
    value: Optional[str] = None
    symbolic_ref: Optional[WitnessArtifact] = None
    notes: Optional[str] = None


class HashBindingsBlock(LiteSpecModel):
    """§3 ``HashBindingsBlock ::= { bindings }``."""

    bindings: list[HashBinding] = []


class GrammarImport(LiteSpecModel):
    """§3 ``GrammarImport ::= { terminal, source, description }``."""

    terminal: Identifier
    source: str
    description: str


# --------------------------------------------------------------------------- #
# §9.16 property lattice / references
# --------------------------------------------------------------------------- #


class PropertyRef(LiteSpecModel):
    """§9.16 ``PropertyRef`` tagged union (explicit | injected)."""

    kind: Literal["explicit", "injected"]
    property: Optional[str] = None
    expr: Optional[str] = None
    check_id: Optional[str] = None
    tier: Optional[str] = None


class ConsequenceStep(LiteSpecModel):
    """§9.16 ``ConsequenceStep``."""

    direction: Literal["weaken_pre", "strengthen_post"]
    from_: Optional[Predicate] = Field(default=None, alias="from")
    to: Optional[Predicate] = None
    evidence: Optional[WitnessArtifact] = None
