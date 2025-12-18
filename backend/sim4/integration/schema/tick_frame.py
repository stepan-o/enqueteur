from __future__ import annotations

from dataclasses import dataclass, field

from .version import IntegrationSchemaVersion
from .room_frame import RoomFrame
from .agent_frame import AgentFrame
from .item_frame import ItemFrame
from .event_frame import EventFrame
from ..render_specs import RoomRenderSpec, AgentRenderSpec


@dataclass(frozen=True)
class TickFrame:
    """Viewer-facing atomic unit for deterministic replay (primitives-only).

    No engine DTOs embedded. All collections are pre-sorted deterministically.
    """

    # Schema + run context
    schema_version: IntegrationSchemaVersion
    run_id: int | None
    episode_id: int | None

    # Timebase (quantized)
    tick_index: int
    time_seconds: float

    # Fully materialized primitives-only entities
    rooms: list[RoomFrame]
    agents: list[AgentFrame]
    items: list[ItemFrame]

    # Events and narrative
    events: list[EventFrame] = field(default_factory=list)
    narrative_fragments: list[dict] = field(default_factory=list)

    # Viewer-facing render contracts (placeholders allowed; deterministic)
    # Sorted by (room_id) and (agent_id), respectively.
    room_render_specs: list[RoomRenderSpec] = field(default_factory=list)
    agent_render_specs: list[AgentRenderSpec] = field(default_factory=list)
