"""Object + workstation substrate components (Sprint 15.1).

Components here are pure data containers (Rust-portable) describing
static object placement plus dynamic workstation/runtime state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class WorkstationStatus(IntEnum):
    """Canonical workstation status codes (stable numeric values)."""

    UNAVAILABLE = 0
    BROKEN = 1
    NOT_OCCUPIED = 2
    RUNNING_IDLE = 3
    PRODUCING_HALF = 4
    PRODUCING_CAPACITY = 5
    PRODUCING_OVERDRIVE = 6


@dataclass
class ObjectRef:
    """Stable object identity reference."""

    object_id: int


@dataclass
class ObjectClass:
    """Class/type code for an object (maps to visuals and production profile)."""

    class_code: str


@dataclass
class ObjectPlacement:
    """Static placement and footprint info (room/tile coordinates)."""

    room_id: int
    tile_x: int
    tile_y: int
    size_w: int
    size_h: int
    orientation: int
    scale: float
    height: Optional[float] = None


@dataclass
class ObjectStats:
    """Dynamic object stats (tick-updated)."""

    durability: float
    efficiency: float


@dataclass
class WorkstationState:
    """Dynamic workstation state (tick-updated)."""

    status_code: int
    occupant_agent_id: Optional[int]
    ticks_in_state: int


@dataclass
class ProductionProfile:
    """Per-class production + wear tuning constants (simulation-facing)."""

    base_output: float
    wear_rate_idle: float
    wear_rate_load: float
    efficiency_decay_idle: float
    efficiency_decay_load: float
    efficiency_recovery_idle: float
    overdrive_multiplier: float
    overdrive_wear_multiplier: float


@dataclass
class FactoryMetrics:
    """World-level production aggregate emitted by workstation systems."""

    factory_input: float
    active_objects: int
    overdrive_objects: int


__all__ = [
    "WorkstationStatus",
    "ObjectRef",
    "ObjectClass",
    "ObjectPlacement",
    "ObjectStats",
    "WorkstationState",
    "ProductionProfile",
    "FactoryMetrics",
]
