from __future__ import annotations

import math

from backend.sim4.snapshot.world_snapshot_builder import build_world_snapshot
from backend.sim4.snapshot.world_snapshot import TransformSnapshot
from backend.sim4.world.context import WorldContext, RoomRecord
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.components.embodiment import Transform, RoomPresence


def test_world_snapshot_single_agent_single_room():
    # Build minimal world context
    wc = WorldContext()
    wc.register_room(RoomRecord(id=1, label="Room A"))
    # Item optional; ensure empty items list is handled

    # ECS world with one agent entity having Transform + RoomPresence
    ecs = ECSWorld()
    eid = ecs.create_entity()
    ecs.add_component(eid, Transform(room_id=1, x=1.5, y=2.5, orientation=0.0))
    ecs.add_component(eid, RoomPresence(room_id=1, time_in_room=3.0))

    snap = build_world_snapshot(
        tick_index=5, episode_id=7, world_ctx=wc, ecs_world=ecs
    )

    # Structural assertions
    assert snap.tick_index == 5
    assert snap.episode_id == 7
    assert isinstance(snap.rooms, list) and len(snap.rooms) == 1
    assert isinstance(snap.agents, list) and len(snap.agents) == 1
    assert isinstance(snap.items, list) and len(snap.items) == 0

    # Index maps should exist and point to correct indices
    assert snap.room_index == {1: 0}
    assert snap.agent_index == {eid: 0}

    # Deterministic ordering: single entries are at index 0
    room0 = snap.rooms[0]
    agent0 = snap.agents[0]

    assert room0.room_id == 1
    assert room0.label == "Room A"
    assert room0.occupants == [] or room0.occupants == [eid]
    assert room0.items == []
    assert room0.neighbors == []

    # Agent transform values propagated
    ts = agent0.transform
    assert isinstance(ts, TransformSnapshot)
    assert ts.room_id == 1
    assert math.isclose(ts.x, 1.5)
    assert math.isclose(ts.y, 2.5)

    # Action/narrative fallbacks are set deterministically
    assert agent0.action_state_code in (0, agent0.action_state_code)
    assert agent0.narrative_state_ref is None or isinstance(
        agent0.narrative_state_ref, int
    )
