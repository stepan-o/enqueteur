from __future__ import annotations

import json
from pathlib import Path


def make_min_frame(tick_index: int, time_seconds: float, episode_id: int | None):
    from backend.sim4.integration.schema import (
        IntegrationSchemaVersion,
        TickFrame,
        RoomFrame,
        AgentFrame,
        ItemFrame,
        EventFrame,
    )

    return TickFrame(
        schema_version=IntegrationSchemaVersion(1, 0, 0),
        run_id=1,
        episode_id=episode_id,
        tick_index=tick_index,
        time_seconds=time_seconds,
        rooms=[],
        agents=[AgentFrame(agent_id=1, room_id=None, x=0.0, y=0.0, action_state_code=0)],
        items=[],
        events=[],
        narrative_fragments=[],
    )


def test_export_run_includes_ui_events(tmp_path: Path):
    from backend.sim4.integration.schema import RunManifest, IntegrationSchemaVersion
    from backend.sim4.integration.exporter import export_run
    from backend.sim4.integration.ui_events import BubbleEvent, BubbleKind, bubble_event_sort_key

    frames = [make_min_frame(0, 0.0, 1)]

    # Deliberately unsorted events (importance 1 then 3) to test exporter sorting
    ui_events = [
        BubbleEvent(tick_index=0, duration_ticks=5, agent_id=2, room_id=None, kind=BubbleKind.DIALOGUE.value, text="b", importance=1),
        BubbleEvent(tick_index=0, duration_ticks=5, agent_id=1, room_id=None, kind=BubbleKind.DIALOGUE.value, text="a", importance=3),
    ]

    manifest = RunManifest(
        schema_version=IntegrationSchemaVersion(1, 0, 0),
        run_id=10,
        world_id=1,
        episode_id=1,
        tick_start=0,
        tick_end=0,
        frame_count=0,
        time_start_seconds=None,
        time_end_seconds=None,
        artifacts={},
        exported_at_utc_ms=None,
    )

    out_dir = tmp_path / "run_with_ui"
    finalized = export_run(out_dir, manifest=manifest, frames=frames, ui_events=ui_events)

    # Check artifact path and file presence
    rel = finalized.artifacts.get("ui_events")
    assert rel == "ui_events/ui_events.jsonl"
    path = out_dir / rel
    assert path.is_file()

    # Verify JSONL order matches sort policy
    with path.open("r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    texts = [d["text"] for d in lines]

    expected = sorted(ui_events, key=bubble_event_sort_key)
    assert texts == [e.text for e in expected]


def test_export_replay_includes_ui_events(tmp_path: Path):
    from backend.sim4.integration.schema import RunManifest, IntegrationSchemaVersion
    from backend.sim4.integration.exporter import export_replay
    from backend.sim4.integration.ui_events import BubbleEvent, BubbleKind

    frames = [make_min_frame(0, 0.0, 1), make_min_frame(1, 0.1, 1)]
    ui_events = [
        BubbleEvent(tick_index=0, duration_ticks=3, agent_id=None, room_id=9, kind=BubbleKind.NARRATION.value, text="room note", importance=0),
    ]

    manifest = RunManifest(
        schema_version=IntegrationSchemaVersion(1, 0, 0),
        run_id=11,
        world_id=2,
        episode_id=1,
        tick_start=0,
        tick_end=0,
        frame_count=0,
        time_start_seconds=None,
        time_end_seconds=None,
        artifacts={},
        exported_at_utc_ms=None,
    )

    out_dir = tmp_path / "replay_with_ui"
    finalized = export_replay(out_dir, manifest=manifest, frames=frames, keyframe_interval=1, ui_events=ui_events)

    rel = finalized.artifacts.get("ui_events")
    assert rel == "ui_events/ui_events.jsonl"
    path = out_dir / rel
    assert path.is_file()
