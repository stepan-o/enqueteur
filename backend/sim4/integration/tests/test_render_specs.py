from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Any


def make_snapshot(
    *,
    tick_index: int = 0,
    time_seconds: float = 0.0,
    episode_id: int | None = 1,
    rooms: Sequence[Any] = (),
    agents: Sequence[Any] = (),
    items: Sequence[Any] = (),
):
    class S:
        __slots__ = ("tick_index", "time_seconds", "episode_id", "rooms", "agents", "items")

        def __init__(self):
            self.tick_index = int(tick_index)
            self.time_seconds = float(time_seconds)
            self.episode_id = episode_id
            self.rooms = list(rooms)
            self.agents = list(agents)
            self.items = list(items)

    return S()


@dataclass
class DummyRoom:
    room_id: int
    label: str = ""
    neighbors: list[int] | None = None


@dataclass
class DummyTransform:
    x: float
    y: float


@dataclass
class DummyAgent:
    agent_id: int
    room_id: int | None = None
    transform: DummyTransform | None = None
    action_state_code: int = 0


def test_tickframe_includes_render_specs_and_is_sorted():
    from backend.sim4.integration.frame_builder import build_tick_frame
    from backend.sim4.integration.render_specs import DEFAULT_ASSETS

    # Intentionally unsorted input
    rooms = [DummyRoom(room_id=3), DummyRoom(room_id=1), DummyRoom(room_id=2)]
    agents = [
        DummyAgent(agent_id=20, transform=DummyTransform(0.123456, -0.987654)),
        DummyAgent(agent_id=5, transform=DummyTransform(2.0, 3.0)),
    ]
    snap = make_snapshot(tick_index=10, time_seconds=1.234567, rooms=rooms, agents=agents)

    frame = build_tick_frame(snap, events=())

    # Render specs must exist and match counts
    assert len(frame.room_render_specs) == len(rooms)
    assert len(frame.agent_render_specs) == len(agents)

    # Sorted by ids
    room_ids = [rs.room_id for rs in frame.room_render_specs]
    agent_ids = [aspec.agent_id for aspec in frame.agent_render_specs]
    assert room_ids == sorted([r.room_id for r in rooms])
    assert agent_ids == sorted([a.agent_id for a in agents])

    # Defaults are stable
    for rs in frame.room_render_specs:
        assert rs.art_ref == DEFAULT_ASSETS.default_room_art_ref
        # Placeholder geometry is quantized and deterministic
        assert rs.world_x == 0.0 and rs.world_y == 0.0
        assert rs.width == 1.0 and rs.height == 1.0
        assert rs.z_layer == 0

    for aspec in frame.agent_render_specs:
        assert aspec.sprite_ref == DEFAULT_ASSETS.default_agent_sprite_ref
        assert aspec.bubble_anchor_dx == DEFAULT_ASSETS.default_bubble_anchor_dx
        assert aspec.bubble_anchor_dy == DEFAULT_ASSETS.default_bubble_anchor_dy


def test_render_specs_float_quantization_and_serialization_determinism():
    import json
    from backend.sim4.integration.frame_builder import build_tick_frame
    from backend.sim4.integration.util.stable_json import stable_json_dumps

    agents = [DummyAgent(agent_id=1, transform=DummyTransform(0.1234567, 0.1999999))]
    snap = make_snapshot(tick_index=0, time_seconds=0.33333333, rooms=[DummyRoom(1)], agents=agents)
    frame_a = build_tick_frame(snap, events=())
    # Build again to compare deterministic bytes
    frame_b = build_tick_frame(snap, events=())

    s_a = stable_json_dumps(frame_a)
    s_b = stable_json_dumps(frame_b)
    assert s_a == s_b, "Render specs must serialize deterministically"

    # Ensure float quantization applied (builder uses placeholder values, but time/agent pos are quantized)
    data = json.loads(s_a)
    assert isinstance(data.get("time_seconds"), float)
    # room_render_specs present with quantized floats
    for rs in data.get("room_render_specs", []):
        assert all(isinstance(rs[k], (int, float, str)) for k in ("world_x", "world_y", "width", "height", "z_layer", "art_ref", "room_id"))

