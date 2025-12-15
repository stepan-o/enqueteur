from dataclasses import dataclass


@dataclass(frozen=True)
class EventFrame:
    """Primitives-only event representation for viewer frames.

    Sorting is handled by the builder; this DTO is pure data.
    """

    tick_index: int
    kind: str
    payload: dict
    agent_id: int | None = None
    room_id: int | None = None
