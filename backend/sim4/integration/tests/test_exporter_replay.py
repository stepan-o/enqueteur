from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def make_frame(
    tick: int,
    time_s: float,
    *,
    run_id: int | None = 1,
    episode_id: int | None = 1,
    agent_pos: tuple[int | None, float, float] | None = (1, 0.0, 0.0),
):
    from backend.sim4.integration.schema import (
        IntegrationSchemaVersion,
        TickFrame,
        RoomFrame,
        AgentFrame,
        ItemFrame,
        EventFrame,
    )

    rooms: list[RoomFrame] = []
    items: list[ItemFrame] = []
    events: list[EventFrame] = []
    agents: list[AgentFrame] = []
    if agent_pos is not None:
        agent_id, x, y = agent_pos
        agents = [AgentFrame(agent_id=1, room_id=None, x=float(x), y=float(y), action_state_code=0)]

    return TickFrame(
        schema_version=IntegrationSchemaVersion(1, 0, 0),
        run_id=run_id,
        episode_id=episode_id,
        tick_index=tick,
        time_seconds=time_s,
        rooms=rooms,
        agents=agents,
        items=items,
        events=events,
        narrative_fragments=[],
    )


def frames_linear(n: int, *, start_tick: int = 0, dt: float = 0.1) -> Iterable:
    """Yield n frames with a single agent moving +1.0 on x per tick deterministically."""
    for i in range(n):
        tick = start_tick + i
        yield make_frame(tick=tick, time_s=(tick * dt), agent_pos=(1, float(i), 0.0))


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _diff_from_dict(d: dict):
    from backend.sim4.integration.frame_diff import FrameDiff, AgentMove
    from backend.sim4.integration.schema import AgentFrame, ItemFrame, EventFrame

    def agent_move(m: dict) -> AgentMove:
        return AgentMove(
            agent_id=int(m["agent_id"]),
            from_room_id=m.get("from_room_id"),
            to_room_id=m.get("to_room_id"),
            from_x=float(m["from_x"]),
            from_y=float(m["from_y"]),
            to_x=float(m["to_x"]),
            to_y=float(m["to_y"]),
        )

    def agent_frame(a: dict) -> AgentFrame:
        return AgentFrame(
            agent_id=int(a["agent_id"]),
            room_id=a.get("room_id"),
            x=float(a["x"]),
            y=float(a["y"]),
            action_state_code=int(a["action_state_code"]),
        )

    def item_frame(it: dict) -> ItemFrame:
        return ItemFrame(
            item_id=int(it["item_id"]),
            room_id=it.get("room_id"),
            x=float(it["x"]),
            y=float(it["y"]),
            kind_code=int(it["kind_code"]),
        )

    return FrameDiff(
        tick_index=int(d["tick_index"]),
        time_seconds=float(d["time_seconds"]),
        rooms=[],
        events=[EventFrame(**e) for e in d.get("events", [])],
        narrative_fragments=list(d.get("narrative_fragments", [])),
        agents_moved=[agent_move(m) for m in d.get("agents_moved", [])],
        agents_spawned=[agent_frame(a) for a in d.get("agents_spawned", [])],
        agents_despawned=[int(x) for x in d.get("agents_despawned", [])],
        items_spawned=[item_frame(it) for it in d.get("items_spawned", [])],
        items_despawned=[int(x) for x in d.get("items_despawned", [])],
    )


def test_replay_export_layout_and_index(tmp_path: Path):
    from backend.sim4.integration.schema import RunManifest, IntegrationSchemaVersion
    from backend.sim4.integration.exporter import export_replay

    seed_manifest = RunManifest(
        schema_version=IntegrationSchemaVersion(1, 0, 0),
        run_id=42,
        world_id=7,
        episode_id=3,
        tick_start=0,
        tick_end=0,
        frame_count=0,
        time_start_seconds=None,
        time_end_seconds=None,
        artifacts={},
        exported_at_utc_ms=1111111111,
    )

    frames = list(frames_linear(6, start_tick=0))  # ticks 0..5
    out = tmp_path / "run_export"
    finalized = export_replay(out, manifest=seed_manifest, frames=frames, keyframe_interval=2)

    # Check layout
    assert (out / "manifest.json").is_file()
    assert (out / "index.json").is_file()
    # Keyframes at 0,2,4; diffs at 1..5
    for k in (0, 2, 4):
        assert (out / "keyframes" / f"{k:06d}.json").is_file()
    for d in (1, 2, 3, 4, 5):
        assert (out / "diffs" / f"{d:06d}.json").is_file(), f"missing diff {d}"

    # Index correctness
    idx = _load_json(out / "index.json")
    assert idx["keyframe_interval"] == 2
    ticks = idx["ticks"]
    # Tick 0: keyframe 0, no diffs
    assert ticks["0"]["keyframe"] == "keyframes/000000.json"
    assert ticks["0"]["diffs"] == []
    # Tick 3: keyframe 2, diffs [3]
    assert ticks["3"]["keyframe"] == "keyframes/000002.json"
    assert ticks["3"]["diffs"] == ["diffs/000003.json"]
    # Tick 5: keyframe 4, diffs [5]
    assert ticks["5"]["keyframe"] == "keyframes/000004.json"
    assert ticks["5"]["diffs"] == ["diffs/000005.json"]


def test_reconstruct_from_index_via_diffs(tmp_path: Path):
    from backend.sim4.integration.schema import RunManifest, IntegrationSchemaVersion
    from backend.sim4.integration.exporter import export_replay
    from backend.sim4.integration.frame_diff import apply_frame_diff

    seed_manifest = RunManifest(
        schema_version=IntegrationSchemaVersion(1, 0, 0),
        run_id=99,
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

    frames = list(frames_linear(8, start_tick=0))  # ticks 0..7
    out = tmp_path / "run_export"
    export_replay(out, manifest=seed_manifest, frames=frames, keyframe_interval=3)

    idx = _load_json(out / "index.json")
    # reconstruct tick 7
    entry = idx["ticks"]["7"]
    # use in-memory keyframe (tick 6) to avoid JSON->dataclass conversion complexities
    key_tick = 6
    base_frame = frames[key_tick]
    # Apply diffs listed in index
    for rel in entry["diffs"]:
        d = _diff_from_dict(_load_json(out / rel))
        base_frame = apply_frame_diff(base_frame, d)

    # Now base_frame should equal frames[7] in relevant fields
    target = frames[7]
    assert base_frame.tick_index == target.tick_index
    assert base_frame.time_seconds == target.time_seconds
    assert len(base_frame.agents) == len(target.agents)
    if base_frame.agents:
        assert base_frame.agents[0].x == target.agents[0].x
        assert base_frame.agents[0].y == target.agents[0].y


def test_scale_memory_sanity_1000_ticks(tmp_path: Path):
    from backend.sim4.integration.schema import RunManifest, IntegrationSchemaVersion
    from backend.sim4.integration.exporter import export_replay

    seed_manifest = RunManifest(
        schema_version=IntegrationSchemaVersion(1, 0, 0),
        run_id=1,
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

    # Use a generator to avoid holding all frames in memory here; exporter must stream
    def gen():
        for f in frames_linear(1000, start_tick=0):
            yield f

    out = tmp_path / "run_export_1k"
    finalized = export_replay(out, manifest=seed_manifest, frames=gen(), keyframe_interval=100)

    # Basic assertions
    assert finalized.frame_count == 1000
    assert (out / "index.json").is_file()
    # spot-check a few files
    assert (out / "keyframes" / "000000.json").is_file()
    assert (out / "keyframes" / "000100.json").is_file()
    assert (out / "diffs" / "000999.json").is_file()
