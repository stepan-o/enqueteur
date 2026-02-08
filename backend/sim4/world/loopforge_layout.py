"""Canonical Loopforge world layout (v0.1).

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
    BRAIN_FORGE = 1
    ASSEMBLY_LINE = 2
    RESONANCE_HALL = 3
    ELEVATOR_CORE = 4
    SUPERVISOR_DECK = 5
    COOLING_VENTS = 6
    LOADING_YARD = 7
    HABITATION_BLOCK = 8
    LOBBY_ENTRY = 9


class RoomKind(IntEnum):
    CORE = 1
    WORK = 2
    SUPPORT = 3
    CONTROL = 4
    PERIMETER = 5
    RESIDENTIAL = 6


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


WORLD_BOUNDS = RoomBounds(min_x=0.0, min_y=0.0, max_x=500.0, max_y=500.0)


def _specs() -> List[LoopforgeRoomSpec]:
    return [
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.BRAIN_FORGE),
            label="Brain Forge",
            kind_code=int(RoomKind.CORE),
            bounds=RoomBounds(min_x=220.0, min_y=260.0, max_x=260.0, max_y=300.0),
            zone="core",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.ASSEMBLY_LINE),
                int(LoopforgeRoomId.RESONANCE_HALL),
                int(LoopforgeRoomId.ELEVATOR_CORE),
                int(LoopforgeRoomId.LOADING_YARD),
                int(LoopforgeRoomId.SUPERVISOR_DECK),
            ),
            tension_tier="high",
            highlight=True,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.ASSEMBLY_LINE),
            label="Assembly Line",
            kind_code=int(RoomKind.WORK),
            bounds=RoomBounds(min_x=260.0, min_y=260.0, max_x=300.0, max_y=280.0),
            zone="work",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.BRAIN_FORGE),
                int(LoopforgeRoomId.COOLING_VENTS),
                int(LoopforgeRoomId.LOADING_YARD),
            ),
            tension_tier="high",
            highlight=False,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.RESONANCE_HALL),
            label="Resonance Hall",
            kind_code=int(RoomKind.WORK),
            bounds=RoomBounds(min_x=180.0, min_y=260.0, max_x=220.0, max_y=280.0),
            zone="work",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.BRAIN_FORGE),
                int(LoopforgeRoomId.HABITATION_BLOCK),
            ),
            tension_tier="high",
            highlight=False,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.ELEVATOR_CORE),
            label="Elevator Core",
            kind_code=int(RoomKind.SUPPORT),
            bounds=RoomBounds(min_x=240.0, min_y=300.0, max_x=260.0, max_y=320.0),
            zone="circulation",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.BRAIN_FORGE),
                int(LoopforgeRoomId.LOBBY_ENTRY),
                int(LoopforgeRoomId.SUPERVISOR_DECK),
            ),
            tension_tier="medium",
            highlight=True,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.SUPERVISOR_DECK),
            label="Supervisor Deck",
            kind_code=int(RoomKind.CONTROL),
            bounds=RoomBounds(min_x=240.0, min_y=240.0, max_x=260.0, max_y=280.0),
            zone="control",
            level=1,
            neighbors=(
                int(LoopforgeRoomId.BRAIN_FORGE),
                int(LoopforgeRoomId.ELEVATOR_CORE),
            ),
            tension_tier="medium",
            highlight=True,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.COOLING_VENTS),
            label="Cooling Vent Farms",
            kind_code=int(RoomKind.SUPPORT),
            bounds=RoomBounds(min_x=260.0, min_y=240.0, max_x=300.0, max_y=260.0),
            zone="support",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.ASSEMBLY_LINE),
            ),
            tension_tier="low",
            highlight=False,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.LOADING_YARD),
            label="Loading Yard",
            kind_code=int(RoomKind.PERIMETER),
            bounds=RoomBounds(min_x=260.0, min_y=280.0, max_x=300.0, max_y=300.0),
            zone="perimeter",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.ASSEMBLY_LINE),
                int(LoopforgeRoomId.BRAIN_FORGE),
            ),
            tension_tier="medium",
            highlight=False,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.HABITATION_BLOCK),
            label="Habitation Block",
            kind_code=int(RoomKind.RESIDENTIAL),
            bounds=RoomBounds(min_x=160.0, min_y=280.0, max_x=200.0, max_y=320.0),
            zone="residential",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.RESONANCE_HALL),
            ),
            tension_tier="low",
            highlight=False,
        ),
        LoopforgeRoomSpec(
            room_id=int(LoopforgeRoomId.LOBBY_ENTRY),
            label="Lobby Entry",
            kind_code=int(RoomKind.CORE),
            bounds=RoomBounds(min_x=240.0, min_y=320.0, max_x=260.0, max_y=360.0),
            zone="core",
            level=0,
            neighbors=(
                int(LoopforgeRoomId.ELEVATOR_CORE),
            ),
            tension_tier="low",
            highlight=True,
        ),
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
        for n in s.neighbors:
            if n not in ids:
                raise ValueError(f"Room {s.room_id} neighbor {n} is unknown")

    # Ensure adjacency is symmetric
    neighbors_by_id = {s.room_id: set(s.neighbors) for s in spec_list}
    for room_id, neighs in neighbors_by_id.items():
        for n in neighs:
            if room_id not in neighbors_by_id.get(n, set()):
                raise ValueError(f"Room {room_id} is not reciprocated by neighbor {n}")


def apply_loopforge_layout(world_ctx: WorldContext) -> None:
    """Register the canonical Loopforge layout into the WorldContext.

    This is a deterministic, data-only operation. It does not mutate runtime
    systems or ECS state, and it does not perform any I/O.
    """
    specs = _specs()
    _validate_layout(specs)
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
            )
        )


__all__ = [
    "LoopforgeRoomId",
    "RoomKind",
    "WORLD_BOUNDS",
    "apply_loopforge_layout",
]
