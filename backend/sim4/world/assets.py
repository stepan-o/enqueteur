# backend/sim4/world/assets.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional
from ..ecs.entity import EntityID


# ============================================================================
# 1. STATIC IDENTITY LAYER
# ============================================================================

@dataclass(frozen=True)
class AssetIdentity:
    """
    Immutable metadata describing an asset *type*.

    This is analogous to:
    - RoomIdentity
    - AgentIdentity
    - WorldIdentity
    - BoardLayoutSpec

    Assets are static: chairs, terminals, crates, toys, consoles, etc.
    """
    id: str                     # canonical asset id, e.g. "chair_basic"
    label: str                  # human-friendly name
    category: str               # "furniture", "machine", "toy", "prop", etc.
    interactable: bool = False  # can agents interact?
    default_state: Optional[Dict] = None  # static default attributes


# ============================================================================
# 2. RUNTIME ASSET INSTANCE (mutable)
# ============================================================================

@dataclass
class AssetInstance:
    """
    Mutable runtime instance of an asset.

    This gets placed *inside rooms*, just like agents.
    """
    asset_id: str                    # "chair_basic"
    identity: AssetIdentity          # immutable metadata
    instance_id: str                 # unique instance ID, e.g. "chair_basic_01"
    room: Optional[str] = None       # room_id where placed
    state: Dict = field(default_factory=dict)  # runtime mutable state


    def place_in_room(self, room_id: str):
        self.room = room_id


    def set_state(self, key: str, value):
        self.state[key] = value


    def get_state(self, key: str, default=None):
        return self.state.get(key, default)
