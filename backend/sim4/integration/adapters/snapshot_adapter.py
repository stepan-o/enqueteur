from typing import TYPE_CHECKING

from ..schema.tick_frame import TickFrame

if TYPE_CHECKING:
    from backend.sim4.snapshot.world_snapshot import WorldSnapshot
    from backend.sim4.snapshot.episode_types import EpisodeNarrativeFragment


def build_tick_frame(
    tick_index: int,
    time_seconds: float,
    world_snapshot: "WorldSnapshot",
    snapshot_diff_summary: dict | None,
    narrative_fragments: list["EpisodeNarrativeFragment"],
    psycho_metrics: dict | None,
) -> TickFrame:
    """Contract placeholder: construct a TickFrame from provided inputs.

    Read-only adapter. Implementation is intentionally omitted in Subsprint 9.1.
    """
    raise NotImplementedError
