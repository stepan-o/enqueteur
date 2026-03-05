"""Work desire and assignment substrate components (Sprint 15.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkDesire:
    """Agent desire-to-work scalar state."""

    value: float
    threshold: float
    increase_rate: float
    last_tick: int


@dataclass
class WorkAssignment:
    """Agent workstation assignment state."""

    object_id: Optional[int]
    load_band: int
    ticks_working: int


__all__ = ["WorkDesire", "WorkAssignment"]
