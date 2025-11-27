"""
Sim3 World Types (Era III)
=========================

This module defines the *full world model* used across Sim3, aligned with
the Era III backend architecture and the StageEpisodeV2 spec.

It is intentionally split into three layers:

1) Identity Layer (static)
   - WorldIdentity
   - RoomIdentity
   - BoardLayoutSpec
   These define what a world *is* before simulation begins.

2) Runtime Layer (mutable world state)
   - RoomState
   - WorldState
   These track per-room tension and other evolving properties.

3) Snapshot Layer (UI-facing)
   - RoomSnapshot
   - WorldSnapshot
   These are produced by the WorldSnapshotBuilder and included in StageEpisodeV2.

This file contains **data structures only**.
No logic, no builders, no simulation code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from typing import Literal


# ---------------------------------------------------------------------------
# Literal types
# ---------------------------------------------------------------------------

TensionTier = Literal["low", "medium", "high", "critical"]


# ===========================================================================
# 1. IDENTITY LAYER (STATIC)
# ===========================================================================
# These structures define worlds BEFORE the simulation runs.
# Loaded from config/world_registry.py.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoomIdentity:
    """
    Static definition of a room/zone inside a world.

    No coordinates yet — those belong to BoardLayoutSpec or runtime builders.
    """

    id: str                         # stable room id; ex: "control_room"
    label: str                      # human-facing label; ex: "Control Room"
    kind: str                       # semantic UI category ("control", "floor", "storage")

    desc: str                       # textual description
    baseTension: float              # 0–1 baseline tension
    hazards: List[str]              # optional hazard tags (may be empty)
    visualTags: Optional[List[str]] = None


@dataclass(frozen=True)
class BoardLayoutSpec:
    """
    Optional static mapping that defines a canonical board layout for UI.

    Rooms are mapped to coordinates (0–1 normalized or small integer grid).
    Frontend uses this to render the Stage map consistently.

    This is optional because the backend can still function without a visual layout.
    """

    id: str                                         # ex: "factory-board-v1"
    coordinates: Dict[str, Dict[str, float]]        # room_id → {"x": float, "y": float}
    sizes: Optional[Dict[str, Dict[str, float]]] = None  # room_id → {"w": float, "h": float}
    ui_hints: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class WorldIdentity:
    """
    The complete static definition of a world.
    Derived from registry data (world_registry.py).

    Contains:
    - identity metadata
    - room definitions
    - adjacency graph
    - optional board layout spec
    """

    id: str                                         # ex: "factory_floor_v1"
    name: str                                       # display name
    desc: str                                       # human-focused description
    size: str                                       # "small" | "medium" | "large"

    rooms: Dict[str, RoomIdentity]                  # room_id → RoomIdentity
    adjacency: Dict[str, List[str]]                 # room_id → neighboring room_ids

    worldTraits: Dict[str, Any]                     # noise, instability, etc.
    layout: Optional[BoardLayoutSpec] = None        # optional canonical board layout


# ===========================================================================
# 2. RUNTIME LAYER (MUTABLE DURING SIM)
# ===========================================================================
# These represent evolving world state during the simulation.
# ---------------------------------------------------------------------------

@dataclass
class RoomState:
    """
    Mutable per-room state during simulation.
    """

    id: str
    currentTension: float            # 0–1
    incidents: int = 0               # count of events in this room
    flags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldState:
    """
    Mutable runtime world state.

    Backed by:
    - WorldIdentity (static)
    - dynamic room states (mutable)
    """

    identity: WorldIdentity
    rooms: Dict[str, RoomState]      # room_id → RoomState

    timeTick: int = 0                # global tick counter


# ===========================================================================
# 3. SNAPSHOT LAYER (UI-FACING)
# ===========================================================================
# Produced by the EpisodeBuilder or WorldSnapshotBuilder.
# These go directly into StageEpisodeV2.world.
# -----------------------------------------------------------------
