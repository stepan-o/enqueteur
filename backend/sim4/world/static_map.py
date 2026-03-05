from __future__ import annotations

"""Static world map data structures (v1).

Semantic, frontend-agnostic map representation for offline exports.
All fields are deterministic, serializable primitives.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .context import RoomBounds


def _bounds_to_dict(bounds: RoomBounds) -> Dict[str, float]:
    return {
        "min_x": float(bounds.min_x),
        "min_y": float(bounds.min_y),
        "max_x": float(bounds.max_x),
        "max_y": float(bounds.max_y),
    }


@dataclass(frozen=True)
class TileRect:
    x: int
    y: int
    w: int
    h: int

    def to_dict(self) -> Dict[str, int]:
        return {"x": int(self.x), "y": int(self.y), "w": int(self.w), "h": int(self.h)}


@dataclass(frozen=True)
class LayerStrGrid:
    encoding: str
    cells: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {"encoding": self.encoding, "cells": list(self.cells)}


@dataclass(frozen=True)
class LayerBoolGrid:
    encoding: str
    cells: List[bool]

    def to_dict(self) -> Dict[str, object]:
        return {"encoding": self.encoding, "cells": [bool(v) for v in self.cells]}


@dataclass(frozen=True)
class RoomStatic:
    room_id: int
    label: str
    kind_code: int
    bounds: RoomBounds
    level: Optional[int]
    zone: Optional[str]
    tile_rect: TileRect

    def to_dict(self) -> Dict[str, object]:
        return {
            "room_id": int(self.room_id),
            "label": self.label,
            "kind_code": int(self.kind_code),
            "bounds": _bounds_to_dict(self.bounds),
            "level": int(self.level) if self.level is not None else None,
            "zone": self.zone,
            "tile_rect": self.tile_rect.to_dict(),
        }


@dataclass(frozen=True)
class DoorStatic:
    door_id: int
    room_a: int
    room_b: int
    is_open: bool
    geometry: Optional[Dict[str, object]] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "door_id": int(self.door_id),
            "room_a": int(self.room_a),
            "room_b": int(self.room_b),
            "is_open": bool(self.is_open),
            "geometry": self.geometry,
        }


@dataclass(frozen=True)
class LayersV1:
    floor: LayerStrGrid
    blocked: LayerBoolGrid
    conveyor: Optional[LayerStrGrid] = None

    def to_dict(self) -> Dict[str, object]:
        d: Dict[str, object] = {
            "floor": self.floor.to_dict(),
            "blocked": self.blocked.to_dict(),
        }
        if self.conveyor is not None:
            d["conveyor"] = self.conveyor.to_dict()
        return d


@dataclass(frozen=True)
class StaticMapV1:
    schema_version: str = "1"
    tile_vocab_version: Optional[str] = None
    world_bounds: RoomBounds = field(default_factory=lambda: RoomBounds(0.0, 0.0, 1.0, 1.0))
    units_per_tile: float = 1.0
    grid_w: int = 0
    grid_h: int = 0
    rooms: List[RoomStatic] = field(default_factory=list)
    layers: LayersV1 | None = None
    doors: List[DoorStatic] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        if self.layers is None:
            raise ValueError("StaticMapV1.layers is required")
        rooms = list(self.rooms)
        doors = list(self.doors)
        rooms.sort(key=lambda r: r.room_id)
        doors.sort(key=lambda d: d.door_id)
        return {
            "schema_version": str(self.schema_version),
            "tile_vocab_version": self.tile_vocab_version,
            "world_bounds": _bounds_to_dict(self.world_bounds),
            "units_per_tile": float(self.units_per_tile),
            "grid_w": int(self.grid_w),
            "grid_h": int(self.grid_h),
            "rooms": [r.to_dict() for r in rooms],
            "layers": self.layers.to_dict(),
            "doors": [d.to_dict() for d in doors],
        }


__all__ = [
    "TileRect",
    "LayerStrGrid",
    "LayerBoolGrid",
    "RoomStatic",
    "DoorStatic",
    "LayersV1",
    "StaticMapV1",
]
