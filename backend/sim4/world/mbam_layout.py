"""Default MBAM world layout for Enqueteur Case 1.

This module is intentionally data-only and deterministic.
It provides a clean, Loopforge-free baseline layout used by demo and tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, List

from .context import WorldContext, RoomRecord, RoomBounds, ObjectRecord
from .static_map import (
    StaticMapV1,
    RoomStatic,
    TileRect,
    LayersV1,
    LayerStrGrid,
    LayerBoolGrid,
    DoorStatic,
)


class MbamRoomId(IntEnum):
    MBAM_LOBBY = 1
    GALLERY_AFFICHES = 2
    SECURITY_OFFICE = 3
    SERVICE_CORRIDOR = 4
    CAFE_DE_LA_RUE = 5


class MbamDoorId(IntEnum):
    LOBBY_SECURITY = 1001
    GALLERY_CORRIDOR = 1002


class RoomKind(IntEnum):
    PUBLIC = 1
    EXHIBIT = 2
    SECURITY = 3
    SERVICE = 4
    STREET = 5


@dataclass(frozen=True)
class DoorSpec:
    door_id: int
    room_a: int
    room_b: int
    is_open: bool = False


@dataclass(frozen=True)
class RoomSpec:
    room_id: int
    label: str
    kind_code: int
    bounds: RoomBounds
    zone: str
    level: int
    neighbors: tuple[int, ...]
    tension_tier: str
    highlight: bool
    height: float


@dataclass(frozen=True)
class ObjectSpec:
    object_id: int
    class_code: str
    room_id: int
    tile_x: int
    tile_y: int
    size_w: int
    size_h: int
    orientation: int = 0
    scale: float = 1.0
    height: float | None = None


WORLD_BOUNDS = RoomBounds(min_x=0.0, min_y=0.0, max_x=32.0, max_y=20.0)
DEFAULT_UNITS_PER_TILE = 1.0


def _room_specs() -> List[RoomSpec]:
    return [
        RoomSpec(
            room_id=int(MbamRoomId.MBAM_LOBBY),
            label="MBAM Lobby",
            kind_code=int(RoomKind.PUBLIC),
            bounds=RoomBounds(min_x=1.0, min_y=6.0, max_x=10.0, max_y=14.0),
            zone="public",
            level=0,
            neighbors=(
                int(MbamRoomId.GALLERY_AFFICHES),
                int(MbamRoomId.SECURITY_OFFICE),
                int(MbamRoomId.CAFE_DE_LA_RUE),
            ),
            tension_tier="low",
            highlight=True,
            height=4.0,
        ),
        RoomSpec(
            room_id=int(MbamRoomId.GALLERY_AFFICHES),
            label="Gallery 1 - Salle des Affiches",
            kind_code=int(RoomKind.EXHIBIT),
            bounds=RoomBounds(min_x=10.0, min_y=4.0, max_x=20.0, max_y=13.0),
            zone="exhibit",
            level=0,
            neighbors=(int(MbamRoomId.MBAM_LOBBY), int(MbamRoomId.SERVICE_CORRIDOR)),
            tension_tier="medium",
            highlight=True,
            height=4.5,
        ),
        RoomSpec(
            room_id=int(MbamRoomId.SECURITY_OFFICE),
            label="Security Office",
            kind_code=int(RoomKind.SECURITY),
            bounds=RoomBounds(min_x=4.0, min_y=14.0, max_x=12.0, max_y=19.0),
            zone="restricted",
            level=0,
            neighbors=(int(MbamRoomId.MBAM_LOBBY),),
            tension_tier="high",
            highlight=True,
            height=3.6,
        ),
        RoomSpec(
            room_id=int(MbamRoomId.SERVICE_CORRIDOR),
            label="Service Corridor",
            kind_code=int(RoomKind.SERVICE),
            bounds=RoomBounds(min_x=20.0, min_y=6.0, max_x=27.0, max_y=11.0),
            zone="restricted",
            level=0,
            neighbors=(int(MbamRoomId.GALLERY_AFFICHES),),
            tension_tier="medium",
            highlight=False,
            height=3.4,
        ),
        RoomSpec(
            room_id=int(MbamRoomId.CAFE_DE_LA_RUE),
            label="Cafe de la Rue",
            kind_code=int(RoomKind.STREET),
            bounds=RoomBounds(min_x=1.0, min_y=1.0, max_x=12.0, max_y=6.0),
            zone="street",
            level=0,
            neighbors=(int(MbamRoomId.MBAM_LOBBY),),
            tension_tier="low",
            highlight=False,
            height=3.2,
        ),
    ]


def _door_specs() -> List[DoorSpec]:
    return [
        DoorSpec(
            door_id=int(MbamDoorId.LOBBY_SECURITY),
            room_a=int(MbamRoomId.MBAM_LOBBY),
            room_b=int(MbamRoomId.SECURITY_OFFICE),
            is_open=False,
        ),
        DoorSpec(
            door_id=int(MbamDoorId.GALLERY_CORRIDOR),
            room_a=int(MbamRoomId.GALLERY_AFFICHES),
            room_b=int(MbamRoomId.SERVICE_CORRIDOR),
            is_open=False,
        ),
    ]


def _object_specs() -> List[ObjectSpec]:
    return [
        ObjectSpec(
            object_id=3001,
            class_code="LOBBY_DESK",
            room_id=int(MbamRoomId.MBAM_LOBBY),
            tile_x=1,
            tile_y=1,
            size_w=2,
            size_h=1,
            height=1.1,
        ),
        ObjectSpec(
            object_id=3002,
            class_code="DISPLAY_CASE",
            room_id=int(MbamRoomId.GALLERY_AFFICHES),
            tile_x=4,
            tile_y=3,
            size_w=3,
            size_h=2,
            height=1.4,
        ),
        ObjectSpec(
            object_id=3003,
            class_code="BENCH",
            room_id=int(MbamRoomId.GALLERY_AFFICHES),
            tile_x=1,
            tile_y=6,
            size_w=2,
            size_h=1,
            height=0.8,
        ),
        ObjectSpec(
            object_id=3004,
            class_code="SECURITY_TERMINAL",
            room_id=int(MbamRoomId.SECURITY_OFFICE),
            tile_x=2,
            tile_y=1,
            size_w=2,
            size_h=1,
            height=1.3,
        ),
        ObjectSpec(
            object_id=3005,
            class_code="DELIVERY_CART",
            room_id=int(MbamRoomId.SERVICE_CORRIDOR),
            tile_x=1,
            tile_y=1,
            size_w=2,
            size_h=1,
            height=1.0,
        ),
        ObjectSpec(
            object_id=3006,
            class_code="CAFE_COUNTER",
            room_id=int(MbamRoomId.CAFE_DE_LA_RUE),
            tile_x=3,
            tile_y=1,
            size_w=3,
            size_h=1,
            height=1.2,
        ),
        ObjectSpec(
            object_id=3007,
            class_code="RECEIPT_PRINTER",
            room_id=int(MbamRoomId.CAFE_DE_LA_RUE),
            tile_x=7,
            tile_y=1,
            size_w=1,
            size_h=1,
            height=0.8,
        ),
        ObjectSpec(
            object_id=3008,
            class_code="BULLETIN_BOARD",
            room_id=int(MbamRoomId.CAFE_DE_LA_RUE),
            tile_x=9,
            tile_y=3,
            size_w=1,
            size_h=1,
            height=1.6,
        ),
    ]


def _validate_layout(specs: Iterable[RoomSpec]) -> None:
    spec_list = list(specs)
    ids = {s.room_id for s in spec_list}
    if len(ids) != len(spec_list):
        raise ValueError("Duplicate room_id detected in MBAM layout")

    for s in spec_list:
        if s.bounds.min_x < WORLD_BOUNDS.min_x or s.bounds.min_y < WORLD_BOUNDS.min_y:
            raise ValueError(f"Room {s.room_id} bounds outside WORLD_BOUNDS (min)")
        if s.bounds.max_x > WORLD_BOUNDS.max_x or s.bounds.max_y > WORLD_BOUNDS.max_y:
            raise ValueError(f"Room {s.room_id} bounds outside WORLD_BOUNDS (max)")
        if s.height <= 0:
            raise ValueError(f"Room {s.room_id} height must be > 0")
        for n in s.neighbors:
            if n not in ids:
                raise ValueError(f"Room {s.room_id} neighbor {n} is unknown")

    neighbors_by_id = {s.room_id: set(s.neighbors) for s in spec_list}
    for room_id, neighs in neighbors_by_id.items():
        for n in neighs:
            if room_id not in neighbors_by_id.get(n, set()):
                raise ValueError(f"Room {room_id} is not reciprocated by neighbor {n}")


def _validate_doors(doors: Iterable[DoorSpec], specs: Iterable[RoomSpec]) -> None:
    door_list = list(doors)
    if not door_list:
        return
    room_ids = {s.room_id for s in specs}
    door_ids = {d.door_id for d in door_list}
    if len(door_ids) != len(door_list):
        raise ValueError("Duplicate door_id detected in MBAM layout")
    neighbors_by_id = {s.room_id: set(s.neighbors) for s in specs}
    for d in door_list:
        if d.room_a not in room_ids or d.room_b not in room_ids:
            raise ValueError(f"Door {d.door_id} references unknown room ids")
        if d.room_b not in neighbors_by_id.get(d.room_a, set()):
            raise ValueError(f"Door {d.door_id} requires neighbors between rooms {d.room_a} and {d.room_b}")


def _validate_objects(objects: Iterable[ObjectSpec], specs: Iterable[RoomSpec]) -> None:
    obj_list = list(objects)
    if not obj_list:
        return
    room_by_id = {s.room_id: s for s in specs}
    obj_ids = {o.object_id for o in obj_list}
    if len(obj_ids) != len(obj_list):
        raise ValueError("Duplicate object_id detected in MBAM layout")

    for o in obj_list:
        room = room_by_id.get(o.room_id)
        if room is None:
            raise ValueError(f"Object {o.object_id} references unknown room {o.room_id}")
        if not o.class_code:
            raise ValueError(f"Object {o.object_id} class_code must be non-empty")
        if o.size_w <= 0 or o.size_h <= 0:
            raise ValueError(f"Object {o.object_id} size_w/size_h must be > 0")
        if o.orientation < 0 or o.orientation > 3:
            raise ValueError(f"Object {o.object_id} orientation must be 0..3")
        if o.scale <= 0:
            raise ValueError(f"Object {o.object_id} scale must be > 0")
        if o.height is not None and o.height <= 0:
            raise ValueError(f"Object {o.object_id} height must be > 0 when provided")

        room_w = room.bounds.max_x - room.bounds.min_x
        room_h = room.bounds.max_y - room.bounds.min_y
        foot_w = o.size_h if (o.orientation % 2 == 1) else o.size_w
        foot_h = o.size_w if (o.orientation % 2 == 1) else o.size_h
        if o.tile_x < 0 or o.tile_y < 0:
            raise ValueError(f"Object {o.object_id} tile origin must be >= 0 within room")
        if (o.tile_x + foot_w) > room_w or (o.tile_y + foot_h) > room_h:
            raise ValueError(f"Object {o.object_id} footprint exceeds room bounds")


def _require_integral_tiles(value: float, label: str) -> int:
    rounded = int(round(value))
    if abs(value - rounded) > 1e-6:
        raise ValueError(f"{label} must align to tile grid; got {value}")
    return rounded


def _bounds_to_tile_rect(bounds: RoomBounds, *, units_per_tile: float) -> TileRect:
    x = (bounds.min_x - WORLD_BOUNDS.min_x) / units_per_tile
    y = (bounds.min_y - WORLD_BOUNDS.min_y) / units_per_tile
    w = (bounds.max_x - bounds.min_x) / units_per_tile
    h = (bounds.max_y - bounds.min_y) / units_per_tile
    return TileRect(
        x=_require_integral_tiles(x, "room bounds min_x"),
        y=_require_integral_tiles(y, "room bounds min_y"),
        w=_require_integral_tiles(w, "room bounds width"),
        h=_require_integral_tiles(h, "room bounds height"),
    )


def _grid_index(x: int, y: int, grid_w: int, grid_h: int) -> int:
    if x < 0 or y < 0 or x >= grid_w or y >= grid_h:
        raise ValueError(f"grid index out of bounds: ({x}, {y})")
    return y * grid_w + x


def _floor_key_for_room(kind_code: int) -> str:
    if kind_code == int(RoomKind.PUBLIC):
        return "FLOOR/PUBLIC/BASE"
    if kind_code == int(RoomKind.EXHIBIT):
        return "FLOOR/EXHIBIT/BASE"
    if kind_code == int(RoomKind.SECURITY):
        return "FLOOR/SECURITY/BASE"
    if kind_code == int(RoomKind.SERVICE):
        return "FLOOR/SERVICE/BASE"
    if kind_code == int(RoomKind.STREET):
        return "FLOOR/STREET/BASE"
    return "FLOOR/GENERIC/BASE"


def _footprint_dims(size_w: int, size_h: int, orientation: int) -> tuple[int, int]:
    if int(orientation) % 2 == 1:
        return int(size_h), int(size_w)
    return int(size_w), int(size_h)


def _build_static_map(
    *,
    room_specs: list[RoomSpec],
    door_specs: list[DoorSpec],
    object_specs: list[ObjectSpec],
    units_per_tile: float,
) -> StaticMapV1:
    width = (WORLD_BOUNDS.max_x - WORLD_BOUNDS.min_x) / units_per_tile
    height = (WORLD_BOUNDS.max_y - WORLD_BOUNDS.min_y) / units_per_tile
    grid_w = _require_integral_tiles(width, "WORLD_BOUNDS width")
    grid_h = _require_integral_tiles(height, "WORLD_BOUNDS height")
    if grid_w <= 0 or grid_h <= 0:
        raise ValueError("Static map grid dimensions must be > 0")

    total = grid_w * grid_h
    floor_cells = ["FLOOR/VOID"] * total
    blocked_cells = [True] * total

    rooms: list[RoomStatic] = []
    rooms_by_id = {r.room_id: r for r in room_specs}
    for spec in sorted(room_specs, key=lambda r: r.room_id):
        rect = _bounds_to_tile_rect(spec.bounds, units_per_tile=units_per_tile)
        key = _floor_key_for_room(spec.kind_code)
        for y in range(rect.y, rect.y + rect.h):
            for x in range(rect.x, rect.x + rect.w):
                idx = _grid_index(x, y, grid_w, grid_h)
                floor_cells[idx] = key
                blocked_cells[idx] = False
        rooms.append(
            RoomStatic(
                room_id=int(spec.room_id),
                label=spec.label,
                kind_code=int(spec.kind_code),
                bounds=spec.bounds,
                level=int(spec.level) if spec.level is not None else None,
                zone=spec.zone,
                tile_rect=rect,
            )
        )

    for obj in sorted(object_specs, key=lambda o: o.object_id):
        room = rooms_by_id.get(obj.room_id)
        if room is None:
            raise ValueError(f"Object {obj.object_id} references unknown room {obj.room_id}")
        room_bounds = room.bounds
        base_x = room_bounds.min_x + (obj.tile_x * units_per_tile)
        base_y = room_bounds.min_y + (obj.tile_y * units_per_tile)
        gx = _require_integral_tiles((base_x - WORLD_BOUNDS.min_x) / units_per_tile, "object tile_x")
        gy = _require_integral_tiles((base_y - WORLD_BOUNDS.min_y) / units_per_tile, "object tile_y")
        foot_w, foot_h = _footprint_dims(obj.size_w, obj.size_h, obj.orientation)
        for y in range(gy, gy + foot_h):
            for x in range(gx, gx + foot_w):
                idx = _grid_index(x, y, grid_w, grid_h)
                blocked_cells[idx] = True

    doors: list[DoorStatic] = []
    for d in sorted(door_specs, key=lambda x: x.door_id):
        doors.append(
            DoorStatic(
                door_id=int(d.door_id),
                room_a=int(d.room_a),
                room_b=int(d.room_b),
                is_open=bool(d.is_open),
                geometry=None,
            )
        )

    layers = LayersV1(
        floor=LayerStrGrid(encoding="RAW", cells=floor_cells),
        blocked=LayerBoolGrid(encoding="RAW", cells=blocked_cells),
        conveyor=None,
    )

    return StaticMapV1(
        schema_version="1",
        tile_vocab_version=None,
        world_bounds=WORLD_BOUNDS,
        units_per_tile=float(units_per_tile),
        grid_w=int(grid_w),
        grid_h=int(grid_h),
        rooms=rooms,
        layers=layers,
        doors=doors,
    )


def apply_mbam_layout(world_ctx: WorldContext) -> None:
    """Register the deterministic MBAM case layout into WorldContext."""
    specs = _room_specs()
    doors = _door_specs()
    objects = _object_specs()
    _validate_layout(specs)
    _validate_doors(doors, specs)
    _validate_objects(objects, specs)

    for s in specs:
        world_ctx.register_room(
            RoomRecord(
                id=s.room_id,
                label=s.label,
                kind_code=s.kind_code,
                bounds=s.bounds,
                zone=s.zone,
                level=s.level,
                neighbors=s.neighbors,
                tension_tier=s.tension_tier,
                highlight=s.highlight,
                height=s.height,
            )
        )

    for d in doors:
        world_ctx.register_door(d.door_id, is_open=d.is_open, room_a=d.room_a, room_b=d.room_b)

    for o in objects:
        world_ctx.register_object(
            ObjectRecord(
                id=o.object_id,
                class_code=o.class_code,
                room_id=o.room_id,
                tile_x=o.tile_x,
                tile_y=o.tile_y,
                size_w=o.size_w,
                size_h=o.size_h,
                orientation=o.orientation,
                scale=o.scale,
                height=o.height,
            )
        )

    world_ctx.static_map = _build_static_map(
        room_specs=list(specs),
        door_specs=list(doors),
        object_specs=list(objects),
        units_per_tile=float(DEFAULT_UNITS_PER_TILE),
    )


__all__ = [
    "MbamRoomId",
    "MbamDoorId",
    "RoomKind",
    "WORLD_BOUNDS",
    "apply_mbam_layout",
]
