from __future__ import annotations

from dataclasses import dataclass


# Helper Snapshot Types


@dataclass(frozen=True)
class AgentSocialSnapshot:
    other_agent_id: int
    relationship: float
    trust: float
    respect: float
    resentment: float
    impression_code: int


@dataclass(frozen=True)
class MotiveSnapshot:
    motive_id: int
    strength: float


@dataclass(frozen=True)
class PlanStepSnapshot:
    step_id: int
    target_agent_id: int | None
    target_room_id: int | None
    target_asset_id: int | None
    status_code: int


@dataclass(frozen=True)
class PlanSnapshot:
    steps: list[PlanStepSnapshot]
    current_index: int
    confidence: float


@dataclass(frozen=True)
class TransformSnapshot:
    room_id: int | None
    x: float
    y: float


# Core Types


@dataclass(frozen=True)
class RoomBoundsSnapshot:
    min_x: float
    min_y: float
    max_x: float
    max_y: float


@dataclass(frozen=True)
class RoomSnapshot:
    room_id: int
    label: str
    kind_code: int
    occupants: list[int]
    items: list[int]
    neighbors: list[int]
    tension_tier: str | None
    highlight: bool | None
    height: float | None = None
    bounds: RoomBoundsSnapshot | None = None
    zone: str | None = None
    level: int | None = None


@dataclass(frozen=True)
class AgentSnapshot:
    agent_id: int
    room_id: int | None

    # Identity & Persona
    role_code: int
    generation: int
    profile_traits: dict[str, float]
    identity_vector: list[float] | None
    persona_style_vector: list[float] | None

    # Drives & Emotion
    drives: dict[str, float]
    emotions: dict[str, float]

    # Social
    key_relationships: list[AgentSocialSnapshot]

    # Intent & Planning
    active_motives: list[MotiveSnapshot]
    plan: PlanSnapshot | None

    # Action & Embodiment
    transform: TransformSnapshot
    action_state_code: int

    # Core Stats
    durability: float
    energy: float
    money: float
    smartness: float
    toughness: float
    obedience: float
    factory_goal_alignment: float

    # Narrative Overlay
    narrative_state_ref: int | None
    cached_summary_ref: int | None


@dataclass(frozen=True)
class ItemSnapshot:
    item_id: int
    room_id: int | None
    owner_agent_id: int | None
    status_code: int
    label: str


@dataclass(frozen=True)
class ObjectSnapshot:
    object_id: int
    class_code: str
    room_id: int
    tile_x: int
    tile_y: int
    size_w: int
    size_h: int
    orientation: int
    scale: float
    height: float | None
    durability: float
    efficiency: float
    status_code: int
    occupant_agent_id: int | None
    ticks_in_state: int


@dataclass(frozen=True)
class WorldSnapshot:
    world_id: int
    tick_index: int
    episode_id: int
    time_seconds: float
    day_index: int
    ticks_per_day: int
    tick_in_day: int
    time_of_day: float
    day_phase: str
    phase_progress: float
    factory_input: float
    rooms: list[RoomSnapshot]
    agents: list[AgentSnapshot]
    items: list[ItemSnapshot]
    objects: list[ObjectSnapshot]
    room_index: dict[int, int] | None
    agent_index: dict[int, int] | None


__all__ = [
    "WorldSnapshot",
    "RoomSnapshot",
    "RoomBoundsSnapshot",
    "AgentSnapshot",
    "ItemSnapshot",
    "ObjectSnapshot",
    "AgentSocialSnapshot",
    "MotiveSnapshot",
    "PlanSnapshot",
    "PlanStepSnapshot",
    "TransformSnapshot",
]
