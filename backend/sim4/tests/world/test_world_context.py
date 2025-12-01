import pytest

from backend.sim4.world.context import (
    WorldContext,
    RoomRecord,
    ItemRecord,
)


def test_register_room_and_duplicate():
    ctx = WorldContext()
    r1 = RoomRecord(id=1, label="A")
    ctx.register_room(r1)
    assert ctx.get_room(1) == r1
    # Duplicate registration should raise
    with pytest.raises(ValueError):
        ctx.register_room(RoomRecord(id=1, label="A again"))


def test_register_agent_and_move_between_rooms():
    ctx = WorldContext()
    ctx.register_room(RoomRecord(id=1, label="A"))
    ctx.register_room(RoomRecord(id=2, label="B"))

    # Unknown room rejected on registration
    with pytest.raises(KeyError):
        ctx.register_agent(agent_id=100, room_id=999)

    # Register properly
    ctx.register_agent(agent_id=100, room_id=1)

    assert ctx.get_agent_room(100) == 1
    assert 100 in ctx.get_room_agents(1)

    # Move to another room
    ctx.move_agent(agent_id=100, new_room_id=2)
    assert ctx.get_agent_room(100) == 2
    assert 100 not in ctx.get_room_agents(1)
    assert 100 in ctx.get_room_agents(2)

    # Moving to unknown room should raise
    with pytest.raises(KeyError):
        ctx.move_agent(agent_id=100, new_room_id=999)

    # Moving unknown agent should raise
    with pytest.raises(KeyError):
        ctx.move_agent(agent_id=999, new_room_id=1)


def test_item_register_and_move_between_rooms_and_none():
    ctx = WorldContext()
    ctx.register_room(RoomRecord(id=1, label="A"))
    ctx.register_room(RoomRecord(id=2, label="B"))

    # Register item in room 1
    item = ItemRecord(id=10, room_id=1)
    ctx.register_item(item)
    assert ctx.items_by_id[10].room_id == 1
    assert 10 in ctx.get_room_items(1)

    # Move item to room 2
    ctx.move_item(item_id=10, new_room_id=2)
    assert ctx.items_by_id[10].room_id == 2
    assert 10 not in ctx.get_room_items(1)
    assert 10 in ctx.get_room_items(2)

    # Move item to None (unplaced)
    ctx.move_item(item_id=10, new_room_id=None)
    assert ctx.items_by_id[10].room_id is None
    assert 10 not in ctx.get_room_items(2)

    # Invalid cases
    with pytest.raises(KeyError):
        ctx.move_item(item_id=999, new_room_id=1)
    with pytest.raises(KeyError):
        ctx.move_item(item_id=10, new_room_id=999)


def test_returned_collections_are_immutable_and_live_updates():
    ctx = WorldContext()
    ctx.register_room(RoomRecord(id=1, label="A"))
    ctx.register_room(RoomRecord(id=2, label="B"))
    ctx.register_agent(agent_id=1, room_id=1)
    ctx.register_item(ItemRecord(id=100, room_id=1))

    agents_view = ctx.get_room_agents(1)
    items_view = ctx.get_room_items(1)

    # Returned frozensets are immutable
    with pytest.raises(AttributeError):
        agents_view.add(2)  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        items_view.add(200)  # type: ignore[attr-defined]

    # Underlying context changes are reflected in new calls
    ctx.move_agent(agent_id=1, new_room_id=2)
    ctx.move_item(item_id=100, new_room_id=None)

    assert 1 not in ctx.get_room_agents(1)
    assert 1 in ctx.get_room_agents(2)
    assert 100 not in ctx.get_room_items(1)
