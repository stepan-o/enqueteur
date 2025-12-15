from __future__ import annotations

from dataclasses import replace

from backend.sim4.integration.schema import (
    IntegrationSchemaVersion,
    TickFrame,
    RoomFrame,
    AgentFrame,
    ItemFrame,
    EventFrame,
)
from backend.sim4.integration.frame_diff import (
    compute_frame_diff,
    apply_frame_diff,
    FrameDiff,
)


def make_frame(
    *,
    tick: int,
    time: float,
    agents: list[AgentFrame],
    rooms: list[RoomFrame] | None = None,
    items: list[ItemFrame] | None = None,
    run_id: int | None = 1,
    episode_id: int | None = 9,
) -> TickFrame:
    rooms = rooms or [RoomFrame(room_id=1, label="A", neighbors=[])]
    items = items or []
    events: list[EventFrame] = []
    return TickFrame(
        schema_version=IntegrationSchemaVersion(1, 0, 0),
        run_id=run_id,
        episode_id=episode_id,
        tick_index=tick,
        time_seconds=time,
        rooms=sorted(rooms, key=lambda r: r.room_id),
        agents=sorted(agents, key=lambda a: a.agent_id),
        items=sorted(items, key=lambda it: it.item_id),
        events=events,
        narrative_fragments=[],
    )


def test_empty_diff_roundtrip():
    prev = make_frame(
        tick=10,
        time=1.0,
        agents=[AgentFrame(agent_id=1, room_id=1, x=0.0, y=0.0, action_state_code=0)],
    )
    curr = replace(prev, tick_index=11, time_seconds=1.1)  # same entities, time advanced

    d = compute_frame_diff(prev, curr)
    assert isinstance(d, FrameDiff)
    # No changes beyond tick/time
    assert d.agents_moved == []
    assert d.agents_spawned == []
    assert d.agents_despawned == []
    assert d.items_spawned == []
    assert d.items_despawned == []

    out = apply_frame_diff(prev, d)
    assert out == curr


def test_agent_movement_only_roundtrip():
    prev = make_frame(
        tick=20,
        time=2.0,
        agents=[
            AgentFrame(agent_id=1, room_id=1, x=0.0, y=0.0, action_state_code=1),
        ],
    )
    curr = make_frame(
        tick=21,
        time=2.1,
        agents=[
            AgentFrame(agent_id=1, room_id=1, x=1.0, y=2.0, action_state_code=1),
        ],
    )

    d = compute_frame_diff(prev, curr)
    assert len(d.agents_moved) == 1
    assert d.agents_moved[0].agent_id == 1
    # Round-trip
    out = apply_frame_diff(prev, d)
    assert out == curr


def test_multiple_agents_moving_roundtrip():
    prev = make_frame(
        tick=30,
        time=3.0,
        agents=[
            AgentFrame(agent_id=1, room_id=1, x=0.0, y=0.0, action_state_code=1),
            AgentFrame(agent_id=2, room_id=1, x=5.0, y=5.0, action_state_code=2),
        ],
    )
    curr = make_frame(
        tick=31,
        time=3.1,
        agents=[
            AgentFrame(agent_id=1, room_id=2, x=0.5, y=0.5, action_state_code=1),
            AgentFrame(agent_id=2, room_id=1, x=6.0, y=5.5, action_state_code=2),
        ],
    )
    d = compute_frame_diff(prev, curr)
    # Deterministic sorting by agent_id
    ids = [m.agent_id for m in d.agents_moved]
    assert ids == sorted(ids)
    out = apply_frame_diff(prev, d)
    assert out == curr


def test_spawn_and_movement_roundtrip():
    # 1 existing agent moves; 1 new agent spawns at non-default position
    prev = make_frame(
        tick=40,
        time=4.0,
        agents=[AgentFrame(agent_id=1, room_id=1, x=0.0, y=0.0, action_state_code=1)],
    )
    curr = make_frame(
        tick=41,
        time=4.1,
        agents=[
            AgentFrame(agent_id=1, room_id=1, x=1.0, y=0.0, action_state_code=1),
            AgentFrame(agent_id=2, room_id=2, x=10.0, y=10.0, action_state_code=0),
        ],
    )
    d = compute_frame_diff(prev, curr)
    # One move, one spawn
    assert len(d.agents_moved) == 1
    assert len(d.agents_spawned) == 1
    assert d.agents_spawned[0].agent_id == 2
    out = apply_frame_diff(prev, d)
    assert out == curr


def test_despawn_roundtrip():
    prev = make_frame(
        tick=50,
        time=5.0,
        agents=[
            AgentFrame(agent_id=1, room_id=1, x=0.0, y=0.0, action_state_code=1),
            AgentFrame(agent_id=2, room_id=1, x=1.0, y=1.0, action_state_code=2),
        ],
        items=[ItemFrame(item_id=10, room_id=1, owner_agent_id=None, status_code=0)],
    )
    curr = make_frame(
        tick=51,
        time=5.1,
        agents=[
            AgentFrame(agent_id=1, room_id=1, x=0.0, y=0.0, action_state_code=1),
        ],
        items=[],
    )
    d = compute_frame_diff(prev, curr)
    assert d.agents_despawned == [2]
    assert d.items_despawned == [10]
    out = apply_frame_diff(prev, d)
    assert out == curr
