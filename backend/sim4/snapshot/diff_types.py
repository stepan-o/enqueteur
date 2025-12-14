from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class AgentDiff:
    agent_id: int
    prev_room_id: int | None
    curr_room_id: int | None
    moved: bool
    position_changed: bool


@dataclass(frozen=True)
class RoomOccupancyDiff:
    room_id: int
    entered_agent_ids: List[int]
    exited_agent_ids: List[int]


@dataclass(frozen=True)
class ItemDiff:
    item_id: int
    prev_room_id: int | None
    curr_room_id: int | None
    spawned: bool
    despawned: bool
    moved: bool


@dataclass(frozen=True)
class SnapshotDiff:
    tick_prev: int
    tick_curr: int
    agent_diffs: Dict[int, AgentDiff]
    room_occupancy: Dict[int, RoomOccupancyDiff]
    item_diffs: Dict[int, ItemDiff]


__all__ = [
    "AgentDiff",
    "RoomOccupancyDiff",
    "ItemDiff",
    "SnapshotDiff",
]
