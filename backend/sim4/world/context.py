"""
WorldContext — Sim4 world-layer runtime substrate (data-only, Sub‑Sprint 5.1).

Scope (SOT-SIM4-WORLD-ENGINE, SOP-100/200):
- Lives under world/ and owns environment state (rooms, agents-in-rooms, items).
- Pure data holder with small registry helpers; NO ECS imports, NO commands/events yet.
- Deterministic, Rust-portable shapes: ints, strings, lists/dicts/sets, dataclasses.

This module defines a minimal WorldContext with:
- Room registry (rooms_by_id)
- Agent↔Room indices (agent_room, room_agents)
- Item registry (items_by_id) and per-room index (room_items)

Mutation via WorldCommands and event emission will be added in later sub-sprints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set, Optional, FrozenSet


# --- Local world-layer ID aliases (do not import from ecs.*) ---
RoomID = int
AgentID = int  # typically ECS EntityID, but kept world-local here
ItemID = int
DoorID = int
ObjectID = int


@dataclass(frozen=True)
class RoomBounds:
    """Axis-aligned bounds for a room footprint in world units."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def __post_init__(self) -> None:
        if not (self.max_x > self.min_x and self.max_y > self.min_y):
            raise ValueError("RoomBounds must satisfy max_x > min_x and max_y > min_y")


@dataclass(frozen=True)
class RoomRecord:
    """
    Lightweight, ID-centric room descriptor with optional spatial metadata.

    Notes:
    - Keep fields deterministic and read-only; world views may expose them.
    - Richer metadata can be added later per SOT-SIM4-WORLD-ENGINE.
    """

    id: RoomID
    label: Optional[str] = None
    kind_code: int = 0
    bounds: RoomBounds | None = None
    zone: Optional[str] = None
    level: int = 0
    neighbors: tuple[RoomID, ...] = ()
    tension_tier: Optional[str] = None
    highlight: Optional[bool] = None
    height: Optional[float] = None

    def __post_init__(self) -> None:
        # Normalize neighbor list to a sorted, unique tuple for determinism.
        if self.neighbors:
            uniq = sorted(set(int(n) for n in self.neighbors))
            object.__setattr__(self, "neighbors", tuple(uniq))
        # Ensure level is non-negative for simple multi-level layout.
        if self.level < 0:
            raise ValueError("RoomRecord.level must be >= 0")
        if self.height is not None and self.height <= 0:
            raise ValueError("RoomRecord.height must be > 0 when provided")


@dataclass
class ItemRecord:
    """
    Minimal item record for world registry.

    - id: stable ItemID
    - room_id: optional RoomID where the item is placed; None means unplaced
    """

    id: ItemID
    room_id: Optional[RoomID] = None


@dataclass(frozen=True)
class ObjectRecord:
    """
    Static object placement record (data-only, immutable).

    - class_code: stable type identifier (viewer maps to visuals)
    - tile_x/tile_y: tile origin within the room bounds (post-orientation footprint)
    - size_w/size_h: footprint in tiles
    - orientation: 0..3 quarter turns (clockwise)
    - scale: optional scalar applied about footprint center
    - height: optional vertical extent in world units (tiles)
    """

    id: ObjectID
    class_code: str
    room_id: RoomID
    tile_x: int
    tile_y: int
    size_w: int
    size_h: int
    orientation: int = 0
    scale: float = 1.0
    height: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.class_code:
            raise ValueError("ObjectRecord.class_code must be non-empty")
        if self.size_w <= 0 or self.size_h <= 0:
            raise ValueError("ObjectRecord size_w/size_h must be > 0")
        if self.orientation < 0 or self.orientation > 3:
            raise ValueError("ObjectRecord.orientation must be 0..3")
        if self.scale <= 0:
            raise ValueError("ObjectRecord.scale must be > 0")
        if self.height is not None and self.height <= 0:
            raise ValueError("ObjectRecord.height must be > 0 when provided")


@dataclass
class WorldContext:
    """
    Mutable runtime context for the world layer (data-only skeleton).

    Responsibilities (5.1):
    - Own registries for rooms, agents, and items.
    - Provide small helper methods to keep indices consistent.

    Layer constraints:
    - Must not import ecs/; runtime will later adapt between ECS and WorldContext.
    - Deterministic operations; explicit errors for invalid inputs.
    """

    rooms_by_id: Dict[RoomID, RoomRecord] = field(default_factory=dict)
    agent_room: Dict[AgentID, RoomID] = field(default_factory=dict)
    room_agents: Dict[RoomID, Set[AgentID]] = field(default_factory=dict)
    items_by_id: Dict[ItemID, ItemRecord] = field(default_factory=dict)
    room_items: Dict[RoomID, Set[ItemID]] = field(default_factory=dict)
    objects_by_id: Dict[ObjectID, ObjectRecord] = field(default_factory=dict)
    room_objects: Dict[RoomID, Set[ObjectID]] = field(default_factory=dict)
    # Doors: minimal boolean state map. Absent key means door unknown.
    door_open: Dict[DoorID, bool] = field(default_factory=dict)

    # ---- Room registry ----
    def register_room(self, room: RoomRecord) -> None:
        """
        Register a new room by ID.

        Raises:
            ValueError: if a room with the same ID already exists.
        """
        if room.id in self.rooms_by_id:
            raise ValueError(f"Room ID already exists: {room.id}")
        self.rooms_by_id[room.id] = room
        # Ensure indices exist lazily on first access; sets are created on demand.

    def get_room(self, room_id: RoomID) -> Optional[RoomRecord]:
        """Return the RoomRecord if present; otherwise None."""
        return self.rooms_by_id.get(room_id)

    # ---- Agent ↔ Room ----
    def register_agent(self, agent_id: AgentID, room_id: RoomID) -> None:
        """
        Place a new agent into an existing room, initializing indices.

        Raises:
            KeyError: if room_id is unknown.
            ValueError: if agent_id is already registered.
        """
        if room_id not in self.rooms_by_id:
            raise KeyError(f"Unknown room_id: {room_id}")
        if agent_id in self.agent_room:
            raise ValueError(f"Agent already registered: {agent_id}")
        self.agent_room[agent_id] = room_id
        self.room_agents.setdefault(room_id, set()).add(agent_id)

    def move_agent(self, agent_id: AgentID, new_room_id: RoomID) -> None:
        """
        Move an existing agent to a different room.

        Updates both agent_room and room_agents indices.

        Raises:
            KeyError: if agent_id is unknown or new_room_id does not exist.
        """
        if agent_id not in self.agent_room:
            raise KeyError(f"Unknown agent_id: {agent_id}")
        if new_room_id not in self.rooms_by_id:
            raise KeyError(f"Unknown room_id: {new_room_id}")

        old_room_id = self.agent_room[agent_id]
        if old_room_id == new_room_id:
            # idempotent no-op: still ensure indices hold the agent once
            return

        # Remove from old room set
        if old_room_id is not None:
            ra = self.room_agents.get(old_room_id)
            if ra is not None:
                ra.discard(agent_id)

        # Add to new room
        self.agent_room[agent_id] = new_room_id
        self.room_agents.setdefault(new_room_id, set()).add(agent_id)

    def get_agent_room(self, agent_id: AgentID) -> Optional[RoomID]:
        """
        Return the current RoomID of the agent, or None if the agent is unknown.
        """
        return self.agent_room.get(agent_id)

    def get_room_agents(self, room_id: RoomID) -> FrozenSet[AgentID]:
        """
        Return an immutable view (frozenset) of agents in the specified room.
        If the room has no agents or is not yet in the index, returns an empty set.
        """
        return frozenset(self.room_agents.get(room_id, set()))

    # ---- Items ----
    def register_item(self, item: ItemRecord) -> None:
        """
        Register a new item and index it by room if placed.

        Raises:
            ValueError: if item.id already exists.
            KeyError: if item.room_id is not None and the room does not exist.
        """
        if item.id in self.items_by_id:
            raise ValueError(f"Item ID already exists: {item.id}")
        if item.room_id is not None and item.room_id not in self.rooms_by_id:
            raise KeyError(f"Unknown room_id for item placement: {item.room_id}")

        self.items_by_id[item.id] = item
        if item.room_id is not None:
            self.room_items.setdefault(item.room_id, set()).add(item.id)

    def move_item(self, item_id: ItemID, new_room_id: Optional[RoomID]) -> None:
        """
        Move an existing item to a different room or to None (unplaced).

        Updates items_by_id[item_id].room_id and per-room indices.

        Args:
            item_id: Item to move.
            new_room_id: Target room, or None to unplace the item.

        Raises:
            KeyError: if item_id is unknown, or if new_room_id is not None and unknown.
        """
        item = self.items_by_id.get(item_id)
        if item is None:
            raise KeyError(f"Unknown item_id: {item_id}")
        if new_room_id is not None and new_room_id not in self.rooms_by_id:
            raise KeyError(f"Unknown room_id: {new_room_id}")

        old_room_id = item.room_id
        if old_room_id == new_room_id:
            return  # idempotent no-op

        # Remove from old index
        if old_room_id is not None:
            ri = self.room_items.get(old_room_id)
            if ri is not None:
                ri.discard(item_id)

        # Update item
        item.room_id = new_room_id

        # Add to new index
        if new_room_id is not None:
            self.room_items.setdefault(new_room_id, set()).add(item_id)

    def get_room_items(self, room_id: RoomID) -> FrozenSet[ItemID]:
        """
        Return an immutable view (frozenset) of item IDs placed in the room.
        If the room has no items or is not yet in the index, returns an empty set.
        """
        return frozenset(self.room_items.get(room_id, set()))

    # ---- Objects ----
    def register_object(self, obj: ObjectRecord) -> None:
        """
        Register a new static object and index it by room.

        Raises:
            ValueError: if object.id already exists.
            KeyError: if obj.room_id is unknown.
        """
        if obj.id in self.objects_by_id:
            raise ValueError(f"Object ID already exists: {obj.id}")
        if obj.room_id not in self.rooms_by_id:
            raise KeyError(f"Unknown room_id for object placement: {obj.room_id}")
        self.objects_by_id[obj.id] = obj
        self.room_objects.setdefault(obj.room_id, set()).add(obj.id)

    def get_room_objects(self, room_id: RoomID) -> FrozenSet[ObjectID]:
        """Return an immutable view (frozenset) of object IDs placed in the room."""
        return frozenset(self.room_objects.get(room_id, set()))

    # ---- Doors ----
    def register_door(self, door_id: DoorID, is_open: bool = False) -> None:
        """Register a door with an initial open/closed state.

        Raises:
            ValueError: if the door_id already exists.
        """
        if door_id in self.door_open:
            raise ValueError(f"Door ID already exists: {door_id}")
        self.door_open[door_id] = bool(is_open)

    def set_door_open(self, door_id: DoorID, is_open: bool) -> None:
        """Set door state to open/closed.

        Raises:
            KeyError: if door_id is unknown.
        """
        if door_id not in self.door_open:
            raise KeyError(f"Unknown door_id: {door_id}")
        self.door_open[door_id] = bool(is_open)

    def is_door_open(self, door_id: DoorID) -> bool:
        """Return True if the door is known and open; raises if unknown.

        Raises:
            KeyError: if door_id is unknown.
        """
        if door_id not in self.door_open:
            raise KeyError(f"Unknown door_id: {door_id}")
        return self.door_open[door_id]

    # Optional thin shim to avoid import cycles for callers that prefer a method
    def apply_world_commands(self, commands):
        """Apply commands via the module-level applier (convenience shim)."""
        from .apply_world_commands import apply_world_commands as _apply
        return _apply(self, commands)

    def make_views(self):
        """Construct a read-only WorldViews façade for this context.

        Lazy import to avoid module import cycles at import time.
        """
        from .views import WorldViews  # local import to prevent circular import
        return WorldViews(self)
