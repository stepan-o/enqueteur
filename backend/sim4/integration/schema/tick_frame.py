from __future__ import annotations

from dataclasses import dataclass

from .version import IntegrationSchemaVersion
from .room_frame import RoomFrame
from .agent_frame import AgentFrame
from .item_frame import ItemFrame
from .event_frame import EventFrame


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
    events: list[EventFrame]
    narrative_fragments: list[dict]
