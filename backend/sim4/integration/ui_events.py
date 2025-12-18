from __future__ import annotations

"""
Sub-Sprint 11.1 — Bubble Event contract (schema + deterministic mapping policy)

This module defines primitives-only DTOs for viewer bubble events and encodes
explicit, deterministic ordering and anchoring rules. It contains NO imports
from runtime/ecs/world/narrative layers (SOP-100) and performs NO I/O, clock
access, RNG, or side effects (SOP-200).

Mapping Policy (canonical guidance for future runtime bridges)
--------------------------------------------------------------
Anchoring rules:
- Agent-anchored: Dialogue and Thought are anchored to the speaking/thinking
  agent. Set agent_id = <agent.id>, room_id = <agent.room_id at tick> (may be
  None if not applicable). Viewers should position the bubble near the agent.
- Room-anchored: Ambient or environmental narration is anchored to a room.
  Set room_id = <room.id>, agent_id = None. Viewers should position the bubble
  using the room’s anchor/centroid.
- Global/Narration (unanchored to agent or room): Use NARRATION with both
  agent_id = None and room_id = None. Viewers may render these as HUD-level
  overlays.

Timebase and duration:
- tick_index is the simulation tick at which the bubble becomes visible.
- duration_ticks is a positive integer (>= 1) declaring how many ticks the
  bubble remains on-screen unless preempted by viewer policy. A bubble that
  starts at tick T with duration D is considered active for ticks
  [T, T + D - 1]. Viewers may interpolate real-time display using their own
  FPS, but the logical visibility window must respect this interval.

Importance and overlap resolution:
- importance is an integer priority; higher numbers indicate higher priority.
- When multiple bubbles compete for display in the same visual region or from
  the same anchor at the same tick, viewers should prefer bubbles with higher
  importance. Lower-importance bubbles may be deferred, stacked, or omitted.
- Deterministic tie-breakers for identical tick and importance are defined by
  the ordering rules below; viewers MUST honor these to ensure stable replay.

Determinism and ordering:
- Given identical inputs, bridges must produce byte-identical BubbleEvents.
- When multiple BubbleEvents occur at the same tick, sort them by the stable
  key tuple: (tick_index, -importance, agent_id, room_id), with None treated
  as greater than any integer for agent_id/room_id. This guarantees a total
  order and ensures reproducible presentation.

Stability rules:
- Same narrative inputs and the same world/agent identities must yield
  identical BubbleEvents (same fields, same order) across runs and platforms.
- Enum values are stable strings (no auto-numbering); safe for Rust ports.

Validation:
- duration_ticks >= 1
- text must be non-empty (after stripping whitespace)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Tuple


class BubbleKind(str, Enum):
    """Stable string enum for bubble kinds.

    Values are strings to maintain cross-language stability and portability.
    Do NOT auto-number.
    """

    DIALOGUE = "DIALOGUE"
    THOUGHT = "THOUGHT"
    NARRATION = "NARRATION"


@dataclass(frozen=True)
class BubbleEvent:
    """Primitives-only DTO for viewer bubble events.

    All fields are JSON-serializable primitives. `kind` is emitted as a stable
    string value.
    """

    tick_index: int
    duration_ticks: int
    agent_id: int | None
    room_id: int | None
    kind: str  # BubbleKind value as string for primitives-only JSON
    text: str
    importance: int

    def __post_init__(self) -> None:
        # Validation (deterministic, pure)
        if int(self.duration_ticks) < 1:
            raise ValueError("duration_ticks must be >= 1")
        if len(str(self.text).strip()) == 0:
            raise ValueError("text must be non-empty")
        # Ensure kind is a stable known value (string) without importing engine
        k = str(self.kind)
        if k not in {k.value for k in BubbleKind}:
            raise ValueError(f"kind must be one of {[k.value for k in BubbleKind]}")


def bubble_event_sort_key(ev: BubbleEvent) -> Tuple[int, int, int, int]:
    """Deterministic ordering key for BubbleEvents.

    Sort by: (tick_index ASC, -importance DESC, agent_id ASC, room_id ASC)
    with None treated as greater than any integer for agent_id/room_id to
    ensure a total order that is stable across runs and platforms.
    """

    def norm_id(v: int | None) -> int:
        # Treat None as greater than any 32-bit ID; use a large sentinel.
        return v if isinstance(v, int) else 2_147_483_647

    return (
        int(ev.tick_index),
        -int(ev.importance),
        norm_id(ev.agent_id),
        norm_id(ev.room_id),
    )


__all__ = ["BubbleKind", "BubbleEvent", "bubble_event_sort_key"]
