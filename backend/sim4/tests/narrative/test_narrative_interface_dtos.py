from __future__ import annotations

from backend.sim4.narrative.interface import NullNarrativeEngine
from backend.sim4.runtime import (
    NarrativeBudget,
    NarrativeTickContext,
    NarrativeEpisodeContext,
    NarrativeUICallContext,
)
from backend.sim4.snapshot.world_snapshot import (
    WorldSnapshot,
    RoomSnapshot,
    AgentSnapshot,
    ItemSnapshot,
    ObjectSnapshot,
    TransformSnapshot,
)
from backend.sim4.snapshot.episode_types import (
    EpisodeMeta,
    EpisodeMood,
    StageEpisodeV2,
)


def make_min_world_snapshot(tick: int = 0, episode_id: int = 1) -> WorldSnapshot:
    rooms: list[RoomSnapshot] = []
    agents: list[AgentSnapshot] = []
    items: list[ItemSnapshot] = []
    objects: list[ObjectSnapshot] = []
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
        world_output=0.0,
        rooms=rooms,
        agents=agents,
        items=items,
        objects=objects,
        doors=[],
        room_index=None,
        agent_index=None,
    )


def make_min_episode(ep_id: int, initial_snapshot: WorldSnapshot) -> StageEpisodeV2:
    meta = EpisodeMeta(
        episode_id=ep_id,
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


def test_null_narrative_engine_tick_jobs_and_episode_and_ui():
    ws = make_min_world_snapshot(tick=1, episode_id=7)
    budget = NarrativeBudget(max_tokens=0, max_ms=0, allow_external_calls=False, tick_stride=1)

    tick_ctx = NarrativeTickContext(
        tick_index=1,
        dt=1.0,
        episode_id=7,
        world_snapshot=ws,
        agent_snapshots=[],
        recent_events=[],
        diff_summary={},
        narrative_budget=budget,
    )

    engine = NullNarrativeEngine()
    out = engine.run_tick_jobs(tick_ctx)

    # Assert types and empties
    assert hasattr(out, "substrate_suggestions")
    assert hasattr(out, "story_fragments")
    assert hasattr(out, "memory_updates")
    assert out.substrate_suggestions == []
    assert out.story_fragments == []
    assert out.memory_updates == []

    # Episode summary path
    ep = make_min_episode(ep_id=7, initial_snapshot=ws)
    ep_ctx = NarrativeEpisodeContext(
        episode_id=7,
        world_snapshot=ws,
        episode=ep,
        history_slice={},
        narrative_budget=budget,
    )
    ep_out = engine.summarize_episode(ep_ctx)
    assert isinstance(ep_out.summary_text, str)
    assert ep_out.summary_text != ""
    assert isinstance(ep_out.character_summaries, dict)
    assert isinstance(ep_out.key_moments, list)
    assert isinstance(ep_out.memory_updates, list)

    # UI describe path
    ui_ctx = NarrativeUICallContext(
        world_snapshot=ws,
        agent_id=None,
        room_id=None,
        narrative_budget=budget,
    )
    ui_txt = engine.describe_scene(ui_ctx)
    assert isinstance(ui_txt.text, str)
    assert ui_txt.text != ""
