"""
World events — canonical, data-only contract for observable world changes.

Scope (Sub‑Sprint 5.2):
- Define string-backed enum WorldEventKind per SOT-SIM4-ECS-COMMANDS-AND-EVENTS
  and SOT-SIM4-WORLD-ENGINE.
- Define frozen WorldEvent dataclass (Rust-portable, deterministic fields).

Notes:
- Types only; emission logic will be implemented by the world command applier
  in later sub-sprints.
- Layer purity: no imports from ecs/, runtime/, snapshot/, or narrative/ (SOP-100).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# --- Local world-layer ID aliases (mirrors world/context.py) ---
RoomID = int
AgentID = int
ItemID = int
DoorID = int


class WorldEventKind(str, Enum):
    """
    String-backed kinds for world events (observable outcomes).

    Stable string values are part of the cross-language contract.
    """

    AGENT_MOVED_ROOM = "agent_moved_room"
    ITEM_SPAWNED = "item_spawned"
    ITEM_DESPAWNED = "item_despawned"
    DOOR_OPENED = "door_opened"
    DOOR_CLOSED = "door_closed"


@dataclass(frozen=True)
class WorldEvent:
    """
    Canonical world-layer event describing an observed change.

    Fields are optional to keep the structure compact and to allow different
    event kinds to populate only the necessary identifiers.

    Examples:
    - agent_moved_room: agent_id, room_id (new), previous_room_id
    - item_spawned: item_id, room_id
    - door_opened/door_closed: door_id
    """

    kind: WorldEventKind

    agent_id: Optional[AgentID] = None
    room_id: Optional[RoomID] = None
    previous_room_id: Optional[RoomID] = None
    item_id: Optional[ItemID] = None
    door_id: Optional[DoorID] = None

    # Optional tick index can be added later when wiring events through runtime.
