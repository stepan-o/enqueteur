from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DummyRoom:
    room_id: int | str
    neighbors: list[int | str] | None = None


@dataclass
class DummyEmotion:
    tension: float | None = None
    mood_valence: float | None = None


@dataclass
class DummyAgent:
    agent_id: int
    room_id: int | str | None = None
    # Optional nested metrics
    tension: float | None = None
    mood_valence: float | None = None
    emotion: DummyEmotion | None = None


class Snapshot:
    __slots__ = ("tick_index", "time_seconds", "episode_id", "rooms", "agents", "items")

    def __init__(self, *, rooms=(), agents=()):
        self.tick_index = 0
        self.time_seconds = 0.0
        self.episode_id = 1
        self.rooms = list(rooms)
        self.agents = list(agents)
        self.items = []


def test_serialization_round_trip_stability():
    from backend.sim4.integration.psycho_topology import build_psycho_topology
    from backend.sim4.integration.util.stable_json import stable_json_dumps

    rooms = [DummyRoom(1, [2]), DummyRoom(2, [1])]
    agents = [DummyAgent(1, room_id=1), DummyAgent(2, room_id=2)]
    snap = Snapshot(rooms=rooms, agents=agents)

    frame_a = build_psycho_topology(snap, tick_index=5)
    frame_b = build_psycho_topology(snap, tick_index=5)

    s_a = stable_json_dumps(frame_a)
    s_b = stable_json_dumps(frame_b)
    assert s_a == s_b

    data = json.loads(s_a)
    assert data["tick_index"] == 5
    assert isinstance(data.get("nodes"), list) and isinstance(data.get("edges"), list)


def test_defaults_missing_metrics_and_occupancy_and_edges():
    from backend.sim4.integration.psycho_topology import build_psycho_topology

    # No neighbor info => edges may be empty
    rooms = [DummyRoom(1), DummyRoom(2)]
    agents = [DummyAgent(1, room_id=1), DummyAgent(2, room_id=1)]
    snap = Snapshot(rooms=rooms, agents=agents)
    frame = build_psycho_topology(snap, tick_index=0)

    # Two nodes (sorted by id)
    assert [n.room_id for n in frame.nodes] == [1, 2]
    # Occupancy for room 1 is 2, room 2 is 0
    m_by_id = {n.room_id: n.metrics for n in frame.nodes}
    assert m_by_id[1].occupancy == 2
    assert m_by_id[2].occupancy == 0
    # Tension defaults to 0.0
    assert m_by_id[1].tension_avg == 0.0 and m_by_id[2].tension_avg == 0.0
    # No edges when neighbors missing
    assert frame.edges == []


def test_order_determinism_under_shuffled_input():
    from backend.sim4.integration.psycho_topology import build_psycho_topology

    base_rooms = [DummyRoom(1, [2, 3]), DummyRoom(2, [1]), DummyRoom(3, [1])]
    base_agents = [DummyAgent(1, room_id=1), DummyAgent(2, room_id=2), DummyAgent(3, room_id=3)]

    snap = Snapshot(rooms=base_rooms, agents=base_agents)
    ref = build_psycho_topology(snap, tick_index=1)
    ref_json = json.dumps(json.loads(__import__("backend.sim4.integration.util.stable_json", fromlist=['']).stable_json_dumps(ref)))

    for i in range(5):
        rs = list(base_rooms)
        as_ = list(base_agents)
        random.Random(100 + i).shuffle(rs)
        random.Random(200 + i).shuffle(as_)
        snap2 = Snapshot(rooms=rs, agents=as_)
        got = build_psycho_topology(snap2, tick_index=1)
        got_json = json.dumps(json.loads(__import__("backend.sim4.integration.util.stable_json", fromlist=['']).stable_json_dumps(got)))
        assert got_json == ref_json


def test_edge_canonicalization_min_max_single_edge():
    from backend.sim4.integration.psycho_topology import build_psycho_topology

    rooms = [DummyRoom(1, [2]), DummyRoom(2, [1])]
    snap = Snapshot(rooms=rooms, agents=())
    frame = build_psycho_topology(snap, tick_index=0)

    # Only one undirected edge should be present: src <= dst ordering
    assert len(frame.edges) == 1
    e = frame.edges[0]
    assert e.src < e.dst
    assert e.kind == "adjacency"
    assert e.weight == 1.0


def test_quantization_applied_to_metrics():
    from backend.sim4.integration.psycho_topology import build_psycho_topology
    from backend.sim4.integration.util.quantize import qf

    # Agent metrics produce non-rounded averages -> quantize
    agents = [
        DummyAgent(1, room_id=1, tension=0.3333333, mood_valence=0.2222222),
        DummyAgent(2, room_id=1, tension=0.6666666, mood_valence=0.7777777),
    ]
    rooms = [DummyRoom(1, []), DummyRoom(2, [])]
    snap = Snapshot(rooms=rooms, agents=agents)
    frame = build_psycho_topology(snap, tick_index=0)

    m_by_id = {n.room_id: n.metrics for n in frame.nodes}
    # Mean tension ~0.5, mood ~0.49999995 -> quantized
    assert m_by_id[1].tension_avg == qf(0.5)
    assert m_by_id[1].mood_valence_avg == qf((0.2222222 + 0.7777777) / 2)


def test_export_includes_psycho_topology_stream(tmp_path: Path):
    from backend.sim4.integration.schema import RunManifest, IntegrationSchemaVersion
    from backend.sim4.integration.exporter import export_run, export_replay
    from backend.sim4.integration.psycho_topology import PsychoTopologyFrame

    # Minimal frames required by exporter
    from backend.sim4.integration.schema import TickFrame, RoomFrame, AgentFrame, ItemFrame, EventFrame

    frames = [
        TickFrame(
            schema_version=IntegrationSchemaVersion(1, 0, 0),
            run_id=1,
            episode_id=1,
            tick_index=0,
            time_seconds=0.0,
            rooms=[], agents=[AgentFrame(agent_id=1, room_id=None, x=0.0, y=0.0, action_state_code=0)], items=[], events=[], narrative_fragments=[],
        ),
        TickFrame(
            schema_version=IntegrationSchemaVersion(1, 0, 0),
            run_id=1,
            episode_id=1,
            tick_index=1,
            time_seconds=0.1,
            rooms=[], agents=[AgentFrame(agent_id=1, room_id=None, x=0.0, y=0.0, action_state_code=0)], items=[], events=[], narrative_fragments=[],
        ),
    ]

    pts = [
        PsychoTopologyFrame(tick_index=0, metrics_schema_version="1.0", nodes=[], edges=[]),
        PsychoTopologyFrame(tick_index=1, metrics_schema_version="1.0", nodes=[], edges=[]),
    ]

    manifest = RunManifest(
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

    # export_run
    out_dir = tmp_path / "run"
    fin = export_run(out_dir, manifest=manifest, frames=frames, psycho_topology=pts)
    rel = fin.artifacts.get("psycho_topology")
    assert rel == "psycho_topology/psycho_topology.jsonl"
    path = out_dir / rel
    assert path.is_file()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["tick_index"] == 0

    # export_replay
    out_dir2 = tmp_path / "replay"
    fin2 = export_replay(out_dir2, manifest=manifest, frames=frames, keyframe_interval=1, psycho_topology=pts)
    rel2 = fin2.artifacts.get("psycho_topology")
    assert rel2 == "psycho_topology/psycho_topology.jsonl"
    assert (out_dir2 / rel2).is_file()
