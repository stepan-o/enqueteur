"""Embodiment substrate components (Sprint 3.2).

These components live primarily in L1 (embodiment & raw perception).
Values are numeric/ID-only; interpretation and range constraints are enforced
by systems, not by the components themselves, per SOT-SIM4-ECS-SUBSTRATE-COMPONENTS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


# ID aliases for physical substrate
RoomID = int
AssetID = int  # defined here so perception.py can import from this module


@dataclass
class Transform:
    """
    Physical transform substrate (L1).

    Represents an agent's room and 2D position.
    Orientation is a simple angle in radians or degrees (convention defined
    in systems, not here).
    """

    room_id: RoomID
    x: float
    y: float
    orientation: float


@dataclass
class Velocity:
    """
    Velocity substrate (L1).

    Simple 2D velocity vector in room-local coordinates.
    """

    dx: float
    dy: float


@dataclass
class RoomPresence:
    """
    Room presence substrate (L1).

    Tracks which room an agent is in and how long they have been there.
    """

    room_id: RoomID
    time_in_room: float


@dataclass
class PathState:
    """
    Path-following substrate (L1).

    Represents an active or inactive movement path, expressed as
    waypoints plus progress along the current segment.

    Systems are responsible for ensuring progress_along_segment stays
    within [0.0, 1.0]; components are passive storage only.
    """

    active: bool
    waypoints: List[Tuple[float, float]]
    current_index: int
    progress_along_segment: float  # expected 0.0–1.0 (enforced by systems)
    path_valid: bool
