from __future__ import annotations

from backend.sim4.snapshot.episode_builder import (
    start_new_episode,
    append_tick_to_episode,
    finalize_episode,
)
from backend.sim4.snapshot.episode_types import EpisodeNarrativeFragment
from backend.sim4.snapshot.world_snapshot import WorldSnapshot


def make_world_snapshot(tick: int, episode_id: int = 1) -> WorldSnapshot:
    # Minimal, deterministic snapshot stub: empty rooms/agents/items
    return WorldSnapshot(
        world_id=0,
        tick_index=tick,
        episode_id=episode_id,
        time_seconds=float(tick),
        day_index=1,
        ticks_per_day=60,
        tick_in_day=tick,
        time_of_day=float(tick) / 60.0,
        day_phase="day",
        phase_progress=0.0,
        factory_input=0.0,
        rooms=[],
        agents=[],
        items=[],
        objects=[],
        room_index=None,
        agent_index=None,
    )


def test_episode_builder_start_and_append_minimal():
    initial = make_world_snapshot(tick=0, episode_id=42)

    ep0 = start_new_episode(episode_id=42, initial_snapshot=initial)

    # Validate initial meta and structures
    assert ep0.meta.episode_id == 42
    assert ep0.meta.tick_start == 0
    assert ep0.meta.tick_end == 0
    assert ep0.meta.duration_seconds == 0.0
    assert ep0.key_world_snapshots == [initial]
    assert ep0.narrative_fragments == []

    # Append first tick
    snap1 = make_world_snapshot(tick=1, episode_id=42)
    ep1 = append_tick_to_episode(
        episode=ep0,
        tick_index=1,
        world_snapshot=snap1,
        world_events=[],
        narrative_fragments=[],
    )

    # Original must be unchanged (immutability)
    assert len(ep0.key_world_snapshots) == 1
    assert ep0.meta.tick_end == 0

    # New episode reflects append
    assert ep1.meta.tick_start == 0
    assert ep1.meta.tick_end == 1
    assert ep1.meta.duration_seconds == 1.0
    assert [s.tick_index for s in ep1.key_world_snapshots] == [0, 1]
    assert ep1.meta.episode_id == 42

    # Append second tick with a narrative fragment
    snap2 = make_world_snapshot(tick=2, episode_id=42)
    frag = EpisodeNarrativeFragment(
        tick_index=2, agent_id=None, room_id=None, text="event", importance=0.5
    )
    ep2 = append_tick_to_episode(
        episode=ep1,
        tick_index=2,
        world_snapshot=snap2,
        world_events=[],
        narrative_fragments=[frag],
    )

    # Immutability again
    assert [s.tick_index for s in ep1.key_world_snapshots] == [0, 1]
    assert len(ep1.narrative_fragments) == 0

    # Ep2 state
    assert [s.tick_index for s in ep2.key_world_snapshots] == [0, 1, 2]
    assert ep2.meta.tick_end == 2
    assert ep2.meta.duration_seconds == 2.0
    assert len(ep2.narrative_fragments) == 1
    assert ep2.narrative_fragments[0].text == "event"

    # Finalize is a no-op
    ep_final = finalize_episode(ep2)
    assert ep_final is ep2
