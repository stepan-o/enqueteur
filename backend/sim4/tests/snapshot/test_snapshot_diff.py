from __future__ import annotations

from backend.sim4.snapshot.world_snapshot import (
    WorldSnapshot,
    RoomSnapshot,
    AgentSnapshot,
    ItemSnapshot,
    ObjectSnapshot,
    TransformSnapshot,
)
from backend.sim4.snapshot.snapshot_diff import (
    compute_snapshot_diff,
    summarize_diff_for_narrative,
)


def make_agent(agent_id: int, room_id: int | None, x: float, y: float) -> AgentSnapshot:
    return AgentSnapshot(
        agent_id=agent_id,
        room_id=room_id,
        role_code=0,
        generation=0,
        profile_traits={},
        identity_vector=[],
        persona_style_vector=None,
        drives={},
        emotions={},
        key_relationships=[],
        active_motives=[],
        plan=None,
        transform=TransformSnapshot(room_id=room_id, x=x, y=y),
        action_state_code=0,
        durability=1.0,
        energy=1.0,
        money=0.0,
        smartness=0.5,
        toughness=0.5,
        obedience=0.5,
        factory_goal_alignment=0.5,
        narrative_state_ref=None,
        cached_summary_ref=None,
    )


def make_room(room_id: int, occupants: list[int]) -> RoomSnapshot:
    return RoomSnapshot(
        room_id=room_id,
        label="",
        kind_code=0,
        occupants=list(sorted(occupants)),
        items=[],
        neighbors=[],
        tension_tier="low",
        highlight=False,
    )


def make_world_snapshot(
    tick: int,
    agents: list[AgentSnapshot],
    rooms: list[RoomSnapshot],
    items: list[ItemSnapshot] | None = None,
    objects: list[ObjectSnapshot] | None = None,
    episode_id: int = 1,
) -> WorldSnapshot:
    agents_sorted = sorted(agents, key=lambda a: a.agent_id)
    rooms_sorted = sorted(rooms, key=lambda r: r.room_id)
    items_list = items or []
    items_sorted = sorted(items_list, key=lambda it: it.item_id)
    objects_list = objects or []
    objects_sorted = sorted(objects_list, key=lambda o: o.object_id)
    agent_index = {a.agent_id: i for i, a in enumerate(agents_sorted)}
    room_index = {r.room_id: i for i, r in enumerate(rooms_sorted)}
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
        rooms=rooms_sorted,
        agents=agents_sorted,
        items=items_sorted,
        objects=objects_sorted,
        room_index=room_index,
        agent_index=agent_index,
    )


def test_snapshot_diff_agent_movement():
    # Agent moves room 1 -> 2, position unchanged
    agent_prev = make_agent(agent_id=10, room_id=1, x=1.0, y=2.0)
    agent_curr = make_agent(agent_id=10, room_id=2, x=1.0, y=2.0)

    prev = make_world_snapshot(
        tick=0,
        agents=[agent_prev],
        rooms=[make_room(1, [10])],
    )
    curr = make_world_snapshot(
        tick=1,
        agents=[agent_curr],
        rooms=[make_room(1, []), make_room(2, [10])],
    )

    diff = compute_snapshot_diff(prev, curr)
    ad = diff.agent_diffs[10]
    assert ad.moved is True
    assert ad.position_changed is False

    # Room occupancy
    assert 1 in diff.room_occupancy and 2 in diff.room_occupancy
    r1 = diff.room_occupancy[1]
    r2 = diff.room_occupancy[2]
    assert r1.exited_agent_ids == [10]
    assert r1.entered_agent_ids == []
    assert r2.entered_agent_ids == [10]
    assert r2.exited_agent_ids == []


def test_snapshot_diff_position_change_no_room_change():
    # Same room, position changes
    agent_prev = make_agent(agent_id=7, room_id=1, x=0.0, y=0.0)
    agent_curr = make_agent(agent_id=7, room_id=1, x=1.0, y=0.0)

    prev = make_world_snapshot(tick=0, agents=[agent_prev], rooms=[make_room(1, [7])])
    curr = make_world_snapshot(tick=1, agents=[agent_curr], rooms=[make_room(1, [7])])

    diff = compute_snapshot_diff(prev, curr)
    ad = diff.agent_diffs[7]
    assert ad.moved is False
    assert ad.position_changed is True
    # No room occupancy changes
    assert diff.room_occupancy == {}


def test_snapshot_diff_item_spawn_despawn():
    # Item A (1) despawns; Item B (2) spawns
    item_a_prev = ItemSnapshot(item_id=1, room_id=1, owner_agent_id=None, status_code=0, label="")
    prev = make_world_snapshot(
        tick=0,
        agents=[],
        rooms=[make_room(1, [])],
        items=[item_a_prev],
    )
    item_b_curr = ItemSnapshot(item_id=2, room_id=2, owner_agent_id=None, status_code=0, label="")
    curr = make_world_snapshot(
        tick=1,
        agents=[],
        rooms=[make_room(1, []), make_room(2, [])],
        items=[item_b_curr],
    )

    diff = compute_snapshot_diff(prev, curr)
    d1 = diff.item_diffs[1]
    d2 = diff.item_diffs[2]

    assert d1.despawned is True and d1.spawned is False and d1.moved is False
    assert d2.spawned is True and d2.despawned is False and d2.moved is False


def test_summarize_diff_for_narrative_shape():
    # One move and one item spawn/despawn
    agent_prev = make_agent(agent_id=3, room_id=1, x=0.0, y=0.0)
    agent_curr = make_agent(agent_id=3, room_id=2, x=0.0, y=0.0)
    prev = make_world_snapshot(
        tick=5,
        agents=[agent_prev],
        rooms=[make_room(1, [3])],
        items=[ItemSnapshot(item_id=9, room_id=1, owner_agent_id=None, status_code=0, label="")],
    )
    curr = make_world_snapshot(
        tick=6,
        agents=[agent_curr],
        rooms=[make_room(1, []), make_room(2, [3])],
        items=[ItemSnapshot(item_id=11, room_id=2, owner_agent_id=None, status_code=0, label="")],
    )

    diff = compute_snapshot_diff(prev, curr)
    summary = summarize_diff_for_narrative(diff)

    # Keys exist
    assert set(summary.keys()) == {
        "moved_agents",
        "room_entries",
        "room_exits",
        "spawned_items",
        "despawned_items",
    }

    # Types and contents
    assert isinstance(summary["moved_agents"], list)
    assert summary["moved_agents"] == [3]
    assert summary["room_entries"] == {"2": [3]}
    assert summary["room_exits"] == {"1": [3]}
    assert summary["spawned_items"] == [11]
    assert summary["despawned_items"] == [9]
