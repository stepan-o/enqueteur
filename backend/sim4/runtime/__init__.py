"""Sim4 runtime package public API (Sprint 6 minimal export).

Exposes clock primitives and the minimal tick pipeline skeleton.
Additional runtime modules (engine, scheduler, etc.) will be added in later
sub-sprints.
"""

from .clock import TickClock, TickIndex, DeltaTime
from .tick import tick, TickResult

__all__ = [
    "TickClock",
    "TickIndex",
    "DeltaTime",
    "tick",
    "TickResult",
]
