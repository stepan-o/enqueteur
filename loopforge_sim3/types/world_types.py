"""
Sim3 World Types (Era III)
=========================

Defines the *full world model* for Sim3, aligned with the Era III backend
architecture and StageEpisodeV2 spec.

Three layers:

1) Identity Layer (static)
   - WorldIdentity
   - RoomIdentity
   - BoardLayoutSpec

2) Runtime Layer (mutable)
   - RoomState
   - WorldState

3) Snapshot Layer (UI-facing)
   - RoomSnapshot
   - WorldSnapshot

All logic for generating snapshots is handled by:
    world_snapshot_builder.py
    episode_builder.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from typing import Literal


# ---------------------------------------------------------------------------
# Literal Types
# ---------------------------------------------------------------------------

TensionTier = Literal["low", "medium", "high", "critical"]


# ============================================================================
# 1. IDENTITY LAYER (STATIC)
# ============================================================================

@dataclass(frozen=True)
class RoomIdentity:
    """
    Static definition of a room/zone before simulation begins.
    """

    id: str
    label: str
    kind: str                    # "control", "floor", "storage", etc.

    desc: str
    baseTension: float           # 0–1
    hazards: List[str]
    visualTags: Optional[List[str]] = None


@dataclass(frozen=True)
class BoardLayoutSpec:
    """
    Optional static board layout used for UI positioning (0–1 space or grid).
    """

    id: str
    coordinates: Dict[str, Dict[str, float]]         # room_id → {"x", "y"}
    sizes: Optional[Dict[str, Dict[str, float]]] = None
    ui_hints: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class WorldIdentity:
    """
    Full static definition of a world.
    """

    id: str
    name: str
    desc: str
    size: str                         # "small" | "medium" | "large"

    rooms: Dict[str, RoomIdentity]    # room_id → RoomIdentity
    adjacency: Dict[str, List[str]]   # room_id → list of neighbor rooms

    worldTraits: Dict[str, Any]       # baseline noise, instability, etc.
    layout: Optional[BoardLayoutSpec] = None


# ============================================================================
# 2. RUNTIME LAYER (MUTABLE)
# ============================================================================

@dataclass
class RoomState:
    """
    Mutable per-room state during simulation.
    """

    id: str
    currentTension: float             # 0–1
    incidents: int = 0
    flags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldState:
    """
    Mutable world-state during simulation.
    """

    identity: WorldIdentity
    rooms: Dict[str, RoomState]       # room_id → RoomState

    timeTick: int = 0


# ============================================================================
# 3. SNAPSHOT LAYER (UI-FACING)
# ============================================================================

@dataclass(frozen=True)
class RoomSnapshot:
    """
    UI-ready representation of a room for StageEpisodeV2.

    Contains:
        - position / size (computed by WorldSnapshotBuilder)
        - adjacency (copied from WorldIdentity)
        - current tension tier (derived from RoomState)
        - baseline + visual tags (from identity)
    """

    id: str
    label: str
    kind: str

    position: Dict[str, float]        # {"x": float, "y": float}
    size: Optional[Dict[str, float]]  # {"w", "h"} or None

    adjacency: List[str]

    tensionTier: TensionTier          # computed from currentTension
    baseTensionTier: TensionTier

    visualTags: Optional[List[str]] = None


@dataclass(frozen=True)
class WorldSnapshot:
    """
    UI-ready snapshot of the full world used in StageEpisodeV2.
    """

    id: str
    name: str
    layoutKind: str                   # from BoardLayoutSpec.id

    rooms: List[RoomSnapshot]
