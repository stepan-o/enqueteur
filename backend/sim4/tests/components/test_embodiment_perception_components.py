from __future__ import annotations

from backend.sim4.ecs.components.embodiment import (
    RoomID,
    Transform,
    Velocity,
    RoomPresence,
    PathState,
)
from backend.sim4.ecs.components.perception import (
    PerceptionSubstrate,
    AttentionSlots,
    SalienceState,
)
from backend.sim4.ecs.entity import EntityID


def test_transform_velocity_room_presence_instantiation():
    room: RoomID = 1
    t = Transform(room_id=room, x=1.0, y=2.0, orientation=0.5)
    v = Velocity(dx=0.1, dy=0.2)
    rp = RoomPresence(room_id=room, time_in_room=3.5)

    assert t.room_id == room
    assert t.x == 1.0 and t.y == 2.0
    assert v.dx == 0.1 and v.dy == 0.2
    assert rp.time_in_room == 3.5


def test_path_state_instantiation():
    waypoints = [(0.0, 0.0), (1.0, 1.0)]
    ps = PathState(
        active=True,
        waypoints=waypoints,
        current_index=0,
        progress_along_segment=0.25,
        path_valid=True,
    )
    assert ps.active is True
    assert ps.waypoints is waypoints
    assert ps.current_index == 0
    assert ps.progress_along_segment == 0.25
    assert ps.path_valid is True


def test_perception_and_attention_instantiation():
    e1: EntityID = 1
    e2: EntityID = 2
    room: RoomID = 10
    asset: int = 5

    perc = PerceptionSubstrate(
        visible_agents=[e1, e2],
        visible_assets=[asset],
        visible_rooms=[room],
        proximity_scores={e1: 0.9, e2: 0.5},
    )
    assert perc.visible_agents == [e1, e2]
    assert perc.proximity_scores[e1] == 0.9

    attn = AttentionSlots(
        focused_agent=e1,
        focused_asset=asset,
        focused_room=room,
        secondary_targets=[e2],
        distraction_level=0.3,
    )
    assert attn.focused_agent == e1
    assert attn.secondary_targets == [e2]
    assert attn.distraction_level == 0.3


def test_salience_state_instantiation():
    room: RoomID = 42
    e1: EntityID = 1

    sal = SalienceState(
        agent_salience={e1: 0.7},
        topic_salience={100: 0.4},
        location_salience={room: 0.9},
    )
    assert sal.agent_salience[e1] == 0.7
    assert sal.topic_salience[100] == 0.4
    assert sal.location_salience[room] == 0.9
