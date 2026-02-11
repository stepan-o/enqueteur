"""Canonical Loopforge world layout (v0.2).

This module defines a deterministic, hand-authored level layout for the
Loopforge "AI brain factory" campus. It is intentionally data-only and
lives in the world layer to keep SOP-100 purity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, List

from .context import WorldContext, RoomRecord, RoomBounds


class LoopforgeRoomId(IntEnum):
    WEAVING_GALLERY = 1
    COGNITION_BREWING = 2
    BURNIN_THEATRE = 3
    LOBBY = 4
    DISPATCH = 5
    SECURITY = 6
    NEURAL_LATTICE = 7
    BRAIN_FORGE = 8
    SHIPPING = 9


class LoopforgeDoorId(IntEnum):
    DISPATCH_SECURITY = 1


class RoomKind(IntEnum):
    CORE = 1
    WORK = 2
    SUPPORT = 3
    CONTROL = 4
    PERIMETER = 5
    RESIDENTIAL = 6


@dataclass(frozen=True)
class LoopforgeDoorSpec:
    door_id: int
    room_a: int
    room_b: int
    is_open: bool = False


@dataclass(frozen=True)
class LoopforgeRoomSpec:
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


WORLD_BOUNDS = RoomBounds(min_x=0.0, min_y=0.0, max_x=35.0, max_y=25.0)

_HEIGHT_BASE = 0.9
_HEIGHT_CONTROL = 1.1
_HEIGHT_CORE = 1.25


def _specs() -> List[LoopforgeRoomSpec]:
    return [
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.WEAVING_GALLERY),
            label="Weaving Gallery",
            kind_code=int(RoomKind.WORK),
            bounds=RoomBounds(min_x=5.0, min_y=2.0, max_x=15.0, max_y=10.0),
            zone="work",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.COGNITION_BREWING),
                int(LoopforgeRoomId.LOBBY),
                int(LoopforgeRoomId.DISPATCH),
            ),
            tension_tier="low",
            highlight=False,
            height=_HEIGHT_BASE,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.COGNITION_BREWING),
            label="Cognition Brewing",
            kind_code=int(RoomKind.WORK),
            bounds=RoomBounds(min_x=15.0, min_y=2.0, max_x=26.0, max_y=10.0),
            zone="work",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.WEAVING_GALLERY),
                int(LoopforgeRoomId.BURNIN_THEATRE),
                int(LoopforgeRoomId.SECURITY),
                int(LoopforgeRoomId.BRAIN_FORGE),
            ),
            tension_tier="medium",
            highlight=False,
            height=_HEIGHT_BASE,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.BURNIN_THEATRE),
            label="Burnin Theatre",
            kind_code=int(RoomKind.SUPPORT),
            bounds=RoomBounds(min_x=28.0, min_y=4.0, max_x=35.0, max_y=12.0),
            zone="support",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.COGNITION_BREWING),
                int(LoopforgeRoomId.SHIPPING),
            ),
            tension_tier="medium",
            highlight=False,
            height=_HEIGHT_BASE,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.LOBBY),
            label="Lobby",
            kind_code=int(RoomKind.CORE),
            bounds=RoomBounds(min_x=1.0, min_y=10.0, max_x=10.0, max_y=16.0),
            zone="core",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.WEAVING_GALLERY),
                int(LoopforgeRoomId.DISPATCH),
            ),
            tension_tier="low",
            highlight=True,
            height=_HEIGHT_CORE,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.DISPATCH),
            label="Dispatch",
            kind_code=int(RoomKind.WORK),
            bounds=RoomBounds(min_x=10.0, min_y=10.0, max_x=14.0, max_y=16.0),
            zone="work",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.LOBBY),
                int(LoopforgeRoomId.WEAVING_GALLERY),
                int(LoopforgeRoomId.SECURITY),
                int(LoopforgeRoomId.NEURAL_LATTICE),
            ),
            tension_tier="medium",
            highlight=False,
            height=_HEIGHT_BASE,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.SECURITY),
            label="Security",
            kind_code=int(RoomKind.CONTROL),
            bounds=RoomBounds(min_x=14.0, min_y=10.0, max_x=18.0, max_y=16.0),
            zone="control",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.DISPATCH),
                int(LoopforgeRoomId.COGNITION_BREWING),
                int(LoopforgeRoomId.BRAIN_FORGE),
            ),
            tension_tier="high",
            highlight=True,
            height=_HEIGHT_CONTROL,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.NEURAL_LATTICE),
            label="Neural Lattice",
            kind_code=int(RoomKind.WORK),
            bounds=RoomBounds(min_x=10.0, min_y=16.0, max_x=20.0, max_y=23.0),
            zone="work",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.DISPATCH),
                int(LoopforgeRoomId.BRAIN_FORGE),
            ),
            tension_tier="high",
            highlight=True,
            height=_HEIGHT_BASE,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.BRAIN_FORGE),
            label="Brain Forge",
            kind_code=int(RoomKind.CORE),
            bounds=RoomBounds(min_x=20.0, min_y=14.0, max_x=28.0, max_y=25.0),
            zone="core",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.SECURITY),
                int(LoopforgeRoomId.COGNITION_BREWING),
                int(LoopforgeRoomId.NEURAL_LATTICE),
                int(LoopforgeRoomId.SHIPPING),
            ),
            tension_tier="high",
            highlight=True,
            height=_HEIGHT_CORE,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.SHIPPING),
            label="Shipping",
            kind_code=int(RoomKind.PERIMETER),
            bounds=RoomBounds(min_x=30.0, min_y=15.0, max_x=35.0, max_y=25.0),
            zone="perimeter",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.BRAIN_FORGE),
                int(LoopforgeRoomId.BURNIN_THEATRE),
            ),
            tension_tier="medium",
            highlight=False,
            height=_HEIGHT_BASE,
        ),
    ]


def _door_specs() -> List[LoopforgeDoorSpec]:
    return [
        LoopforgeDoorSpec(
            door_id=int(LoopforgeDoorId.DISPATCH_SECURITY),
            room_a=int(LoopforgeRoomId.DISPATCH),
            room_b=int(LoopforgeRoomId.SECURITY),
            is_open=False,
        )
    ]


def _validate_layout(specs: Iterable[LoopforgeRoomSpec]) -> None:
    spec_list = list(specs)
    ids = {s.room_id for s in spec_list}
    if len(ids) != len(spec_list):
        raise ValueError("Duplicate room_id detected in Loopforge layout")

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

    # Ensure adjacency is symmetric
    neighbors_by_id = {s.room_id: set(s.neighbors) for s in spec_list}
    for room_id, neighs in neighbors_by_id.items():
        for n in neighs:
            if room_id not in neighbors_by_id.get(n, set()):
                raise ValueError(f"Room {room_id} is not reciprocated by neighbor {n}")


def _validate_doors(doors: Iterable[LoopforgeDoorSpec], specs: Iterable[LoopforgeRoomSpec]) -> None:
    door_list = list(doors)
    if not door_list:
        return
    room_ids = {s.room_id for s in specs}
    door_ids = {d.door_id for d in door_list}
    if len(door_ids) != len(door_list):
        raise ValueError("Duplicate door_id detected in Loopforge layout")
    neighbors_by_id = {s.room_id: set(s.neighbors) for s in specs}
    for d in door_list:
        if d.room_a not in room_ids or d.room_b not in room_ids:
            raise ValueError(f"Door {d.door_id} references unknown room ids")
        if d.room_b not in neighbors_by_id.get(d.room_a, set()):
            raise ValueError(
                f"Door {d.door_id} requires neighbors between rooms {d.room_a} and {d.room_b}"
            )


def apply_loopforge_layout(world_ctx: WorldContext) -> None:
    """Register the canonical Loopforge layout into the WorldContext.

    This is a deterministic, data-only operation. It does not mutate runtime
    systems or ECS state, and it does not perform any I/O.
    """
    specs = _specs()
    doors = _door_specs()
    _validate_layout(specs)
    _validate_doors(doors, specs)
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
        world_ctx.register_door(d.door_id, is_open=d.is_open)


__all__ = [
    "LoopforgeRoomId",
    "LoopforgeDoorId",
    "RoomKind",
    "WORLD_BOUNDS",
    "apply_loopforge_layout",
]
