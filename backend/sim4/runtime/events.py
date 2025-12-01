"""
Runtime events — minimal consolidation layer (Sprint 6.5).

Scope:
- Provide a simple, Rust-portable runtime-level event envelope (RuntimeEvent).
- Provide consolidate_events(...) to flatten per-origin events into a single
  deterministic list for a tick (Phase G in runtime.tick).

SOT alignment:
- SOT-SIM4-RUNTIME-TICK §4.7 Event Consolidation — events from world/ecs/runtime
  are ordered deterministically and wrapped for downstream consumers
  (history/snapshot/narrative). This module does not implement an EventBus;
  it only shapes and orders events for the current tick result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Literal

from backend.sim4.world.events import WorldEvent


EventOrigin = Literal["world", "ecs", "runtime"]


@dataclass(frozen=True)
class RuntimeEvent:
    """
    Runtime-level event envelope used in Phase G.

    Fields:
        tick_index: tick this event belongs to.
        seq: stable, per-tick sequence index (0..N-1).
        origin: "world", "ecs", or "runtime".
        payload: underlying event object (WorldEvent for 6.5; ECS/runtime later).

    Notes:
        - Provides a uniform carrier format for later history/snapshot/narrative.
        - seq is stable within a tick and deterministic across runs.
    """

    tick_index: int
    seq: int
    origin: EventOrigin
    payload: Any


def consolidate_events(
    *,
    tick_index: int,
    dt: float,  # currently unused; kept for SOT evolution
    world_events: Iterable[WorldEvent],
    ecs_events: Iterable[Any] = (),
    runtime_events: Iterable[Any] = (),
) -> List[RuntimeEvent]:
    """
    Build a deterministic, flat list of RuntimeEvent for this tick.

    Ordering policy (6.5):
        1) All world_events in the order provided.
        2) Then ecs_events.
        3) Then runtime_events.

    Caller is responsible for passing lists in deterministic order.
    """
    wrapped: List[RuntimeEvent] = []
    seq = 0

    for ev in world_events:
        wrapped.append(RuntimeEvent(tick_index=tick_index, seq=seq, origin="world", payload=ev))
        seq += 1

    for ev in ecs_events:
        wrapped.append(RuntimeEvent(tick_index=tick_index, seq=seq, origin="ecs", payload=ev))
        seq += 1

    for ev in runtime_events:
        wrapped.append(RuntimeEvent(tick_index=tick_index, seq=seq, origin="runtime", payload=ev))
        seq += 1

    return wrapped


__all__ = ["RuntimeEvent", "EventOrigin", "consolidate_events"]
