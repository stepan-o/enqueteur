from __future__ import annotations

"""
Episode builder (Sub‑Sprint 7.4): minimal scaffolding only.

Responsibilities (per SOT-SIM4-SNAPSHOT-AND-EPISODE §6.2 and sprint brief):
- Create a new StageEpisodeV2 from the first WorldSnapshot.
- Append ticks deterministically, returning a new StageEpisodeV2 each time.
- Update only simple bookkeeping fields; perform no narrative or simulation logic.

Hard constraints:
- No imports from runtime/, ecs/, world/, or narrative/.
- No mutation of inputs; always construct new frozen dataclasses for returns.
- No RNG, no timestamps, no I/O.
"""

from dataclasses import replace
from typing import List

from backend.sim4.snapshot.world_snapshot import WorldSnapshot
from backend.sim4.snapshot.episode_types import (
    EpisodeMeta,
    EpisodeMood,
    StageEpisodeV2,
    EpisodeNarrativeFragment,
)


def start_new_episode(
    episode_id: int,
    initial_snapshot: WorldSnapshot,
) -> StageEpisodeV2:
    """
    Initialize a new StageEpisodeV2 from the first snapshot.

    Behavior:
    - meta: empty title/synopsis, tick_start = tick_end = initial tick, duration_seconds=0.0
    - mood: neutral zeros
    - days: empty (placeholder policy deferred)
    - key_world_snapshots: [initial_snapshot]
    - key_agent_timelines: {}
    - narrative_fragments: []
    """

    meta = EpisodeMeta(
        episode_id=episode_id,
        title="",
        synopsis="",
        tick_start=initial_snapshot.tick_index,
        tick_end=initial_snapshot.tick_index,
        duration_seconds=0.0,
        created_at_ms=None,
    )

    mood = EpisodeMood(
        tension_avg=0.0,
        tension_peak=0.0,
        sentiment_valence=0.0,
        social_cohesion=0.0,
        summary_label=None,
    )

    return StageEpisodeV2(
        meta=meta,
        mood=mood,
        days=[],
        key_world_snapshots=[initial_snapshot],
        key_agent_timelines={},
        narrative_fragments=[],
    )


def append_tick_to_episode(
    episode: StageEpisodeV2,
    tick_index: int,
    world_snapshot: WorldSnapshot,
    world_events: List["WorldEvent"],
    narrative_fragments: List[EpisodeNarrativeFragment],
) -> StageEpisodeV2:
    """
    Return a new StageEpisodeV2 with bookkeeping updates only.

    Updates:
    - key_world_snapshots appended with world_snapshot
    - narrative_fragments extended by provided fragments
    - meta.tick_end set to tick_index
    - meta.duration_seconds = tick_end - tick_start (simple stub)

    Notes:
    - world_events are accepted but currently ignored per minimal scope.
    - No mutation of the incoming episode; all lists/maps are copied.
    """

    # Copy/extend lists deterministically without mutating inputs
    new_snapshots = list(episode.key_world_snapshots)
    new_snapshots.append(world_snapshot)

    new_fragments = list(episode.narrative_fragments)
    if narrative_fragments:
        new_fragments.extend(narrative_fragments)

    # Update meta: new tick_end and derived duration
    new_meta = EpisodeMeta(
        episode_id=episode.meta.episode_id,
        title=episode.meta.title,
        synopsis=episode.meta.synopsis,
        tick_start=episode.meta.tick_start,
        tick_end=tick_index,
        duration_seconds=float(tick_index - episode.meta.tick_start),
        created_at_ms=episode.meta.created_at_ms,
    )

    return StageEpisodeV2(
        meta=new_meta,
        mood=episode.mood,  # unchanged neutral/stub
        days=list(episode.days),  # keep structure stable; copy for immutability hygiene
        key_world_snapshots=new_snapshots,
        key_agent_timelines=dict(episode.key_agent_timelines),
        narrative_fragments=new_fragments,
    )


def finalize_episode(
    episode: StageEpisodeV2,
) -> StageEpisodeV2:
    """
    Lifecycle hook: no-op finalization for Sub‑Sprint 7.4.

    Returns the episode unchanged (no summarization or aggregation yet).
    """

    return episode


__all__ = [
    "start_new_episode",
    "append_tick_to_episode",
    "finalize_episode",
]
