"""Sim4 runtime package public API (Sprint 6 minimal export).

Exposes clock primitives needed by the upcoming tick pipeline.
Additional runtime modules (engine, scheduler, etc.) will be added in later
sub-sprints.
"""

from .clock import TickClock, TickIndex, DeltaTime

__all__ = [
    "TickClock",
    "TickIndex",
    "DeltaTime",
]
