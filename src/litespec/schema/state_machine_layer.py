"""State machine layer schema (§7)."""

from __future__ import annotations

from typing import Any, Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import ActionContext
from litespec.schema.primitives import Identifier, IntOrConfig


class StateVarRange(LiteSpecModel):
    """§7.1 ``StateVarRange ::= { min_size?, max_size? }``."""

    min_size: Optional[int] = None
    max_size: Optional[IntOrConfig] = None


class StateVar(LiteSpecModel):
    """§7.1 ``StateVar ::= { name, type, description, range?, default? }``."""

    name: Identifier
    type: str  # TypeExpr, serialized as a §7.2 string
    description: str
    range: Optional[StateVarRange] = None
    default: Optional[Any] = None


class InitPredicate(LiteSpecModel):
    """§7.1 ``InitPredicate ::= { description, expression }``."""

    description: str
    expression: str


class Action(LiteSpecModel):
    """§7.1 ``Action``."""

    name: Identifier
    trigger: str
    guard: str
    effect: str  # EffectExpr (serialized; parsed into the LIR AST)
    fairness: Optional[str] = None
    context: ActionContext
    max_stack_depth: Optional[int] = None
    allowed_calls: Optional[list[str]] = None
    requires_params: Optional[list[str]] = None


class StateMachineLayer(LiteSpecModel):
    """§7.1 ``StateMachineLayer``."""

    state_variables: list[StateVar] = []
    init: InitPredicate
    actions: list[Action] = []
    fairness: Optional[str] = None
