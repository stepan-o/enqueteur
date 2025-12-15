from dataclasses import dataclass
from typing import TYPE_CHECKING

from .version import IntegrationSchemaVersion

# Type-only imports to avoid runtime coupling
if TYPE_CHECKING:
    from backend.sim4.snapshot.world_snapshot import WorldSnapshot
    from backend.sim4.snapshot.episode_types import EpisodeNarrativeFragment


@dataclass(frozen=True)
class TickFrame:
    """Viewer-facing atomic unit for deterministic replay.

    Pure DTO, stable ordering, Rust-portable fields only.
    """

    # Schema + run context
    schema_version: IntegrationSchemaVersion
    run_id: int | None
    episode_id: int | None

    # Timebase
    tick_index: int
    time_seconds: float

    # Snapshot embedding (DTO type from engine; safe under TYPE_CHECKING import)
    world_snapshot: "WorldSnapshot"

    # Event and narrative payloads normalized to plain dicts
    events: list[dict]
    narrative_fragments: list[dict]
