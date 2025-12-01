import dataclasses
import pytest

from backend.sim4.world.commands import (
    WorldCommandKind,
    WorldCommand,
    make_set_agent_room,
    make_spawn_item,
    make_despawn_item,
    make_open_door,
    make_close_door,
)

from backend.sim4.world.events import (
    WorldEventKind,
    WorldEvent,
)


def test_command_construction_set_agent_room_direct_and_helper():
    # Direct construction
    cmd_direct = WorldCommand(seq=1, kind=WorldCommandKind.SET_AGENT_ROOM, agent_id=7, room_id=3)
    assert cmd_direct.kind is WorldCommandKind.SET_AGENT_ROOM
    assert cmd_direct.agent_id == 7
    assert cmd_direct.room_id == 3
    # unused fields are None
    assert cmd_direct.item_id is None and cmd_direct.door_id is None

    # Helper construction
    cmd_helper = make_set_agent_room(seq=2, agent_id=8, room_id=4)
    assert cmd_helper.kind is WorldCommandKind.SET_AGENT_ROOM
    assert cmd_helper.agent_id == 8
    assert cmd_helper.room_id == 4
    assert cmd_helper.item_id is None and cmd_helper.door_id is None


def test_command_construction_spawn_and_door_commands():
    spawn = make_spawn_item(seq=5, item_id=101, room_id=9)
    assert spawn.kind is WorldCommandKind.SPAWN_ITEM
    assert spawn.item_id == 101 and spawn.room_id == 9
    assert spawn.agent_id is None and spawn.door_id is None

    despawn = make_despawn_item(seq=6, item_id=101)
    assert despawn.kind is WorldCommandKind.DESPAWN_ITEM
    assert despawn.item_id == 101 and despawn.room_id is None

    open_cmd = make_open_door(seq=7, door_id=55)
    assert open_cmd.kind is WorldCommandKind.OPEN_DOOR
    assert open_cmd.door_id == 55 and open_cmd.agent_id is None and open_cmd.item_id is None

    close_cmd = make_close_door(seq=8, door_id=55)
    assert close_cmd.kind is WorldCommandKind.CLOSE_DOOR
    assert close_cmd.door_id == 55


def test_event_construction_and_fields():
    moved = WorldEvent(
        kind=WorldEventKind.AGENT_MOVED_ROOM,
        agent_id=10,
        previous_room_id=1,
        room_id=2,
    )
    assert moved.kind is WorldEventKind.AGENT_MOVED_ROOM
    assert moved.agent_id == 10
    assert moved.previous_room_id == 1
    assert moved.room_id == 2

    item_spawned = WorldEvent(kind=WorldEventKind.ITEM_SPAWNED, item_id=200, room_id=9)
    assert item_spawned.kind is WorldEventKind.ITEM_SPAWNED
    assert item_spawned.item_id == 200 and item_spawned.room_id == 9

    door_opened = WorldEvent(kind=WorldEventKind.DOOR_OPENED, door_id=5)
    assert door_opened.kind is WorldEventKind.DOOR_OPENED
    assert door_opened.door_id == 5


def test_enum_values_stable_strings():
    assert WorldCommandKind.SET_AGENT_ROOM.value == "set_agent_room"
    assert WorldCommandKind.SPAWN_ITEM.value == "spawn_item"
    assert WorldCommandKind.DESPAWN_ITEM.value == "despawn_item"
    assert WorldCommandKind.OPEN_DOOR.value == "open_door"
    assert WorldCommandKind.CLOSE_DOOR.value == "close_door"

    assert WorldEventKind.AGENT_MOVED_ROOM.value == "agent_moved_room"
    assert WorldEventKind.ITEM_SPAWNED.value == "item_spawned"
    assert WorldEventKind.ITEM_DESPAWNED.value == "item_despawned"
    assert WorldEventKind.DOOR_OPENED.value == "door_opened"
    assert WorldEventKind.DOOR_CLOSED.value == "door_closed"


def test_frozen_dataclass_immutability():
    cmd = make_set_agent_room(seq=0, agent_id=1, room_id=2)
    evt = WorldEvent(kind=WorldEventKind.ITEM_DESPAWNED, item_id=9)

    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.seq = 99  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        evt.kind = WorldEventKind.ITEM_SPAWNED  # type: ignore[misc]
