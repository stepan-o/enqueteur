"""
Sim4 world package public API (Sprint 5 integration pass).

This module re-exports the core world-layer types and functions to present a
small, cohesive surface area for downstream callers (primarily runtime):

from sim4.world import (
    WorldContext,
    RoomRecord,
    ItemRecord,
    WorldCommand,
    WorldCommandKind,
    WorldEvent,
    WorldEventKind,
    apply_world_commands,
    WorldViews,
    RoomView,
)

Layer purity: This package does not import ecs/ or runtime/ (SOP-100).
"""

from .context import (
    WorldContext,
    RoomRecord,
    RoomBounds,
    ItemRecord,
    ObjectRecord,
    WorldTimeState,
    RoomID,
    AgentID,
    ItemID,
    DoorID,
    ObjectID,
)
from .commands import (
    WorldCommand,
    WorldCommandKind,
    make_set_agent_room,
    make_spawn_item,
    make_despawn_item,
    make_open_door,
    make_close_door,
)
from .events import WorldEvent, WorldEventKind
from .apply_world_commands import apply_world_commands
from .views import WorldViews, RoomView, WorldTimeView
from .loopforge_layout import (
    apply_loopforge_layout,
    WORLD_BOUNDS,
    LoopforgeRoomId,
    LoopforgeDoorId,
    RoomKind,
)
from .static_map import (
    StaticMapV1,
    RoomStatic,
    DoorStatic,
    LayersV1,
    LayerStrGrid,
    LayerBoolGrid,
    TileRect,
)

__all__ = [
    # IDs & records / context
    "WorldContext",
    "RoomRecord",
    "RoomBounds",
    "ItemRecord",
    "ObjectRecord",
    "WorldTimeState",
    "RoomID",
    "AgentID",
    "ItemID",
    "DoorID",
    "ObjectID",
    # Commands & helpers
    "WorldCommand",
    "WorldCommandKind",
    "make_set_agent_room",
    "make_spawn_item",
    "make_despawn_item",
    "make_open_door",
    "make_close_door",
    # Events
    "WorldEvent",
    "WorldEventKind",
    # Applier
    "apply_world_commands",
    # Views
    "WorldViews",
    "RoomView",
    "WorldTimeView",
    # Loopforge layout
    "apply_loopforge_layout",
    "WORLD_BOUNDS",
    "LoopforgeRoomId",
    "LoopforgeDoorId",
    "RoomKind",
    # Static map
    "StaticMapV1",
    "RoomStatic",
    "DoorStatic",
    "LayersV1",
    "LayerStrGrid",
    "LayerBoolGrid",
    "TileRect",
]
