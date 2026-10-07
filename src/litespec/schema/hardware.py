"""Hardware encoding layer schema (§8)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import AssertionFormat, EncodingStrategy, OverflowBehavior, TimingKind
from litespec.schema.primitives import Identifier, IntOrConfig, SpecId


class Signal(LiteSpecModel):
    """§8.1 ``Signal ::= { name, width, description }``."""

    name: Identifier
    width: IntOrConfig
    description: str


class TransitionCycle(LiteSpecModel):
    """§8.1 ``TransitionCycle``."""

    name: Identifier
    input_signals: list[Identifier] = []
    output_signals: list[Identifier] = []
    timing_constraint: str
    timing_kind: TimingKind
    max_cycles: Optional[int] = None


class HWAssertion(LiteSpecModel):
    """§8.1 ``HWAssertion ::= { expression, format, description }``."""

    expression: str
    format: AssertionFormat
    description: str


class TypeEncoding(LiteSpecModel):
    """§8.1 ``TypeEncoding``."""

    tla_type: str
    isr_encoding: str
    width: Optional[IntOrConfig] = None
    max_size: Optional[IntOrConfig] = None
    components: Optional[list[Signal]] = None
    overflow_behavior: OverflowBehavior
    overflow_assertion: Optional[str] = None
    encoding_strategy: EncodingStrategy
    symbolic_encoding: Optional[str] = None


class ClockDomain(LiteSpecModel):
    """§8.1 ``ClockDomain``."""

    name: Identifier
    frequency: int
    resolution: int
    power_state: list[str] = []
    switch_cost: Optional[int] = None


class HardwareEncodingLayer(LiteSpecModel):
    """§8.1 ``HardwareEncodingLayer``."""

    target_isir_id: SpecId
    state_signals: list[Signal] = []
    transition_cycle: TransitionCycle
    assertions: list[HWAssertion] = []
    type_encoding: list[TypeEncoding] = []
    interrupt_stack_size: Optional[int] = None
    clock_domains: Optional[list[ClockDomain]] = None
