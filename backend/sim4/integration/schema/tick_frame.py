from dataclasses import dataclass
from typing import TYPE_CHECKING

# Type-only imports to avoid runtime coupling
if TYPE_CHECKING:
    from backend.sim4.snapshot.world_snapshot import WorldSnapshot
    from backend.sim4.snapshot.episode_types import EpisodeNarrativeFragment


@dataclass(frozen=True)
class TickFrame:
    """Viewer-facing atomic unit for deterministic replay.

    No logic, no mutation. Contains summarized diff and optional psycho metrics.
    """

    tick_index: int
    time_seconds: float

    world_snapshot: "WorldSnapshot"
    snapshot_diff: dict | None

    narrative_fragments: list["EpisodeNarrativeFragment"]

    psycho_metrics: dict | None
