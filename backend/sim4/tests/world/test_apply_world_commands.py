import pytest

from backend.sim4.world.context import WorldContext, RoomRecord
from backend.sim4.world.commands import (
    make_set_agent_room,
    make_spawn_item,
    make_open_door,
    WorldCommand,
    WorldCommandKind,
)
from backend.sim4.world.events import WorldEventKind
from backend.sim4.world.apply_world_commands import apply_world_commands


def test_set_agent_room_basic_flow():
    ctx = WorldContext()
    # Rooms and agent
    ctx.register_room(RoomRecord(id=1, label="A"))
    ctx.register_room(RoomRecord(id=2, label="B"))
    ctx.register_agent(agent_id=100, room_id=1)

    cmd = make_set_agent_room(seq=5, agent_id=100, room_id=2)
    events = apply_world_commands(ctx, [cmd])

    # World state updated
    assert ctx.get_agent_room(100) == 2
    assert 100 not in ctx.get_room_agents(1)
    assert 100 in ctx.get_room_agents(2)

    # Event correctness
    assert len(events) == 1
    evt = events[0]
    assert evt.kind is WorldEventKind.AGENT_MOVED_ROOM
    assert evt.agent_id == 100
    assert evt.previous_room_id == 1
    assert evt.room_id == 2


def test_spawn_item_basic_flow():
    ctx = WorldContext()
    ctx.register_room(RoomRecord(id=1, label="A"))

    cmd = make_spawn_item(seq=1, item_id=10, room_id=1)
    events = apply_world_commands(ctx, [cmd])

    # World state reflects item placement
    assert 10 in ctx.items_by_id
    assert 10 in ctx.get_room_items(1)

    # Event correctness
    assert len(events) == 1
    evt = events[0]
    assert evt.kind is WorldEventKind.ITEM_SPAWNED
    assert evt.item_id == 10
    assert evt.room_id == 1


def test_open_door_basic_flow():
    ctx = WorldContext()
    # Register a door in closed state
    ctx.register_door(door_id=77, is_open=False)

    cmd = make_open_door(seq=3, door_id=77)
    events = apply_world_commands(ctx, [cmd])

    assert ctx.is_door_open(77) is True
    assert len(events) == 1
    assert events[0].kind is WorldEventKind.DOOR_OPENED
    assert events[0].door_id == 77


def test_batch_ordering_and_determinism():
    ctx = WorldContext()
    ctx.register_room(RoomRecord(id=1, label="A"))
    ctx.register_room(RoomRecord(id=2, label="B"))
    ctx.register_agent(agent_id=1, room_id=1)

    # Out-of-order by construction; seq enforces order
    cmd_late = make_set_agent_room(seq=10, agent_id=1, room_id=2)
    cmd_early = make_spawn_item(seq=5, item_id=99, room_id=1)

    events = apply_world_commands(ctx, [cmd_late, cmd_early])

    # Events should be in seq order: spawn (seq 5) then move (seq 10)
    assert [e.kind for e in events] == [WorldEventKind.ITEM_SPAWNED, WorldEventKind.AGENT_MOVED_ROOM]
    # World state reflects both
    assert 99 in ctx.get_room_items(1)
    assert ctx.get_agent_room(1) == 2


def test_error_behavior_no_event_on_failure():
    ctx = WorldContext()
    ctx.register_room(RoomRecord(id=1, label="A"))
    # Agent not registered; move should fail
    bad_cmd = make_set_agent_room(seq=0, agent_id=123, room_id=1)

    with pytest.raises(KeyError):
        apply_world_commands(ctx, [bad_cmd])

    # Ensure that a batch where the first fails does not emit partial events
    # by wrapping two commands where the first is invalid; no events should be returned
    good_cmd = make_spawn_item(seq=1, item_id=10, room_id=1)
    with pytest.raises(KeyError):
        apply_world_commands(ctx, [bad_cmd, good_cmd])


def test_unhandled_command_kind_raises():
    ctx = WorldContext()
    # Fabricate a command with an unknown kind using the dataclass directly
    bogus = WorldCommand(seq=0, kind="__bogus__")  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        apply_world_commands(ctx, [bogus])
