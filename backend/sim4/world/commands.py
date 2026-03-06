"""
World commands — canonical, data-only contract for world-layer mutations.

Scope (Sub‑Sprint 5.2):
- Define string-backed enum WorldCommandKind per SOT-SIM4-ECS-COMMANDS-AND-EVENTS.
- Define frozen WorldCommand dataclass (Rust-portable, deterministic fields).
- Provide small helper constructors for common command kinds.

Notes:
- This module is types-only; no application/mutation logic is implemented here.
- Layer purity: world/ must not import from ecs/, runtime/, etc. (SOP-100).
- Determinism: only primitive, serializable shapes (dataclasses, ints, enums) (SOP-200).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# --- Local world-layer ID aliases (do not import from ecs.*) ---
RoomID = int
AgentID = int  # typically ECS EntityID, but kept world-local here
ItemID = int
DoorID = int


class WorldCommandKind(str, Enum):
    """
    String-backed kinds for world mutation commands (SOT-SIM4-ECS-COMMANDS-AND-EVENTS).

    Stable string values are part of the cross-language contract.
    The set is intentionally minimal in 5.2 and can be extended in later sprints.
    """

    SET_AGENT_ROOM = "set_agent_room"
    SPAWN_ITEM = "spawn_item"
    DESPAWN_ITEM = "despawn_item"
    OPEN_DOOR = "open_door"
    CLOSE_DOOR = "close_door"
    # Reserved for future: SET_ITEM_STATE = "set_item_state"


@dataclass(frozen=True)
class WorldCommand:
    """
    Canonical world-layer command (data-only, Sim4 prototype; Rust-portable).

    Fields:
    - seq: tick-local monotonic sequence number assigned by dispatcher.
    - kind: command kind (WorldCommandKind).
    - agent_id, room_id, item_id, door_id: optional targets; only some are used per kind.
    - state_code / flags: optional numeric payloads reserved for compact state changes.

    Semantics per kind (high level):
    - set_agent_room: move/place an agent in a room (agent_id, room_id required).
    - spawn_item: create/place item in a room (item_id, room_id required).
    - despawn_item: remove item from world (item_id required).
    - open_door/close_door: toggle door state (door_id required).
    """

    seq: int
    kind: WorldCommandKind

    agent_id: Optional[AgentID] = None
    room_id: Optional[RoomID] = None
    item_id: Optional[ItemID] = None
    door_id: Optional[DoorID] = None

    state_code: Optional[int] = None
    flag: Optional[int] = None


# ---- Helper constructors ----
def make_set_agent_room(seq: int, agent_id: AgentID, room_id: RoomID) -> WorldCommand:
    """Helper to build a SET_AGENT_ROOM command."""
    return WorldCommand(
        seq=seq,
        kind=WorldCommandKind.SET_AGENT_ROOM,
        agent_id=agent_id,
        room_id=room_id,
    )


def make_spawn_item(seq: int, item_id: ItemID, room_id: RoomID) -> WorldCommand:
    """Helper to build a SPAWN_ITEM command (place item in room)."""
    return WorldCommand(
        seq=seq,
        kind=WorldCommandKind.SPAWN_ITEM,
        item_id=item_id,
        room_id=room_id,
    )


def make_despawn_item(seq: int, item_id: ItemID) -> WorldCommand:
    """Helper to build a DESPAWN_ITEM command."""
    return WorldCommand(
        seq=seq,
        kind=WorldCommandKind.DESPAWN_ITEM,
        item_id=item_id,
    )


def make_open_door(seq: int, door_id: DoorID) -> WorldCommand:
    """Helper to build an OPEN_DOOR command."""
    return WorldCommand(
        seq=seq,
        kind=WorldCommandKind.OPEN_DOOR,
        door_id=door_id,
    )


def make_close_door(seq: int, door_id: DoorID) -> WorldCommand:
    """Helper to build a CLOSE_DOOR command."""
    return WorldCommand(
        seq=seq,
        kind=WorldCommandKind.CLOSE_DOOR,
        door_id=door_id,
    )
