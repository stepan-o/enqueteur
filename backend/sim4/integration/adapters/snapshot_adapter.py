from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence

from ..schema import TickFrame
from ..schema.version import IntegrationSchemaVersion
from ..frame_builder import build_tick_frame as _build_canonical
from ..types import WorldSnapshotLike

if TYPE_CHECKING:
    from backend.sim4.snapshot.world_snapshot import WorldSnapshot


def build_tick_frame(
    world_snapshot: WorldSnapshotLike,
    recent_events: Sequence[Any],
    narrative_fragments: Sequence[Any] | None = None,
    *,
    schema_version: IntegrationSchemaVersion | None = None,
    run_id: int | None = None,
) -> TickFrame:
    """Thin adapter delegating to the canonical primitives-only frame builder.

    Keeps the public API stable for runtime callers while switching the
    underlying contract to the new primitives-only viewer TickFrame.
    """
    return _build_canonical(
        world_snapshot=world_snapshot,
        events=recent_events,
        narrative_fragments=narrative_fragments or (),
        schema_version=schema_version,
        run_id=run_id,
    )
