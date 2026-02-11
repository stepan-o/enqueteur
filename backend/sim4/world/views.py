"""
World read-only views — façade over WorldContext for systems/runtime.

Scope (Sub‑Sprint 5.4):
- Provide immutable, read-only queries backed by WorldContext state.
- No mutation APIs; never expose mutable internal structures directly.
- Layer-pure: world/ only; no imports from ecs/, runtime/, etc. (SOP-100).

These views will be constructed by the runtime and injected into ECS systems
via structural typing (WorldViewsHandle Protocol) without importing ECS here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Optional, Tuple

from .context import WorldContext, RoomID, AgentID, ItemID, DoorID, ObjectID


@dataclass(frozen=True)
class RoomView:
    """
    Immutable snapshot of a room's occupants and items at query time.

    Notes:
    - agents/items are FrozenSet to prevent callers from mutating indices.
    - This is a light DTO; authoritative data remains in WorldContext.
    """

    room_id: RoomID
    agents: FrozenSet[AgentID]
    items: FrozenSet[ItemID]


class WorldViews:
    """
    Concrete world-layer read-only views for systems/runtime.

    Wraps a WorldContext and exposes safe query methods. All methods return
    immutable containers (frozenset/tuple) and never expose internal sets or dicts.
    """

    def __init__(self, world_ctx: WorldContext) -> None:
        self._world_ctx = world_ctx

    # --- Agent location ---
    def get_agent_room(self, agent_id: AgentID) -> Optional[RoomID]:
        """Return the RoomID where the agent is located, or None if unknown.

        Mirrors WorldContext.get_agent_room semantics.
        """

        return self._world_ctx.get_agent_room(agent_id)

    # --- Room occupants ---
    def get_room_agents(self, room_id: RoomID) -> FrozenSet[AgentID]:
        """Return an immutable set of agents present in the given room.

        Always returns a frozenset; empty if room has no agents or is unknown.
        """

        return self._world_ctx.get_room_agents(room_id)

    # --- Room items ---
    def get_room_items(self, room_id: RoomID) -> FrozenSet[ItemID]:
        """Return an immutable set of items present in the given room.

        Always returns a frozenset; empty if room has no items or is unknown.
        """

        return self._world_ctx.get_room_items(room_id)

    # --- Room objects ---
    def get_room_objects(self, room_id: RoomID) -> FrozenSet[ObjectID]:
        """Return an immutable set of objects present in the given room."""
        return self._world_ctx.get_room_objects(room_id)

    # --- Door state ---
    def is_door_open(self, door_id: DoorID) -> bool:
        """Return True if the specified door is known and open.

        Propagates KeyError if the door ID is unknown (mirrors WorldContext).
        """

        return self._world_ctx.is_door_open(door_id)

    # --- Composite room view ---
    def get_room_view(self, room_id: RoomID) -> RoomView:
        """Return an immutable RoomView for the specified room ID.

        Uses read-only queries to build a lightweight snapshot DTO. The DTO is
        detached and cannot be used to mutate world state.
        """

        return RoomView(
            room_id=room_id,
            agents=self.get_room_agents(room_id),
            items=self.get_room_items(room_id),
        )

    # --- Optional: neighbor/adjacency queries ---
    def iter_room_neighbors(self, room_id: RoomID) -> Iterable[RoomID]:
        """Iterate neighbor rooms for navigation/visibility queries.

        Returns the room's declared neighbor IDs (if any), sorted and immutable.
        """
        rec = self._world_ctx.get_room(room_id)
        if rec is None or not rec.neighbors:
            return ()
        return rec.neighbors
