"""Board configuration schema (§11)."""

from __future__ import annotations

from typing import Optional

from litespec.schema.base import LiteSpecModel
from litespec.schema.enums import ClockSource
from litespec.schema.primitives import Identifier


class CacheConfig(LiteSpecModel):
    l1_icache_kb: Optional[int] = None
    l1_dcache_kb: Optional[int] = None
    l2_kb: Optional[int] = None


class CPUConfig(LiteSpecModel):
    architecture: str
    cores: int
    frequency_mhz: int
    cache: Optional[CacheConfig] = None


class MemoryConfig(LiteSpecModel):
    ram_kb: int
    flash_kb: int
    ecc: bool


class PeripheralConfig(LiteSpecModel):
    name: Identifier
    base_address: int
    irq: Optional[int] = None
    dma: bool


class PowerDomainConfig(LiteSpecModel):
    name: Identifier
    voltage_mv: int
    max_current_ma: int


class ClockDomainConfig(LiteSpecModel):
    name: Identifier
    frequency_hz: int
    source: ClockSource


class BoardConfiguration(LiteSpecModel):
    """§11 ``BoardConfiguration``."""

    name: Identifier
    cpu: CPUConfig
    memory: MemoryConfig
    peripherals: list[PeripheralConfig] = []
    power_domains: list[PowerDomainConfig] = []
    clock_domains: list[ClockDomainConfig] = []
