from __future__ import annotations

from typing import Protocol, Sequence, Any, runtime_checkable


@runtime_checkable
class WorldSnapshotLike(Protocol):
    """Structural protocol for snapshots consumed by the frame builder.

    Captures only the attributes the builder reads, keeping integration
    decoupled from concrete engine DTOs (SOP-100) while allowing type-checkers
    to validate dummy/test snapshots.
    """

    tick_index: int
    time_seconds: float
    episode_id: int | None

    # Entity collections used by the builder; element types are intentionally
    # untyped (Any) to avoid importing engine DTOs at runtime.
    rooms: Sequence[Any]
    agents: Sequence[Any]
    items: Sequence[Any]
