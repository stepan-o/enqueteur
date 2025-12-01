import pytest

from backend.sim4.world.context import WorldContext, RoomRecord
from backend.sim4.world.commands import (
    make_set_agent_room,
    make_spawn_item,
    make_open_door,
)
from backend.sim4.world.apply_world_commands import apply_world_commands
from backend.sim4.world.views import WorldViews, RoomView


def test_views_reflect_world_state_after_commands():
    ctx = WorldContext()
    # Setup rooms and agent
    ctx.register_room(RoomRecord(id=1, label="A"))
    ctx.register_room(RoomRecord(id=2, label="B"))
    ctx.register_agent(agent_id=100, room_id=1)
    ctx.register_door(door_id=7, is_open=False)

    # Apply commands to move agent, spawn item, and open door
    cmds = [
        make_set_agent_room(seq=2, agent_id=100, room_id=2),
        make_spawn_item(seq=1, item_id=10, room_id=2),
        make_open_door(seq=3, door_id=7),
    ]
    apply_world_commands(ctx, cmds)

    views = WorldViews(ctx)

    # Agent location
    assert views.get_agent_room(100) == 2
    assert 100 in views.get_room_agents(2)
    assert 100 not in views.get_room_agents(1)

    # Items
    assert 10 in views.get_room_items(2)
    assert 10 not in views.get_room_items(1)

    # Door state
    assert views.is_door_open(7) is True

    # Composite room view
    room_view: RoomView = views.get_room_view(2)
    assert room_view.room_id == 2
    assert 100 in room_view.agents
    assert 10 in room_view.items


def test_views_immutability_and_no_aliasing():
    ctx = WorldContext()
    ctx.register_room(RoomRecord(id=1, label="A"))
    ctx.register_room(RoomRecord(id=2, label="B"))
    ctx.register_agent(agent_id=1, room_id=1)
    # Spawn item via world command to keep invariants consistent
    apply_world_commands(ctx, [make_spawn_item(seq=0, item_id=99, room_id=1)])

    views = WorldViews(ctx)

    agents_view = views.get_room_agents(1)
    items_view = views.get_room_items(1)

    # Immutability (frozenset)
    assert isinstance(agents_view, frozenset)
    assert isinstance(items_view, frozenset)
    with pytest.raises(AttributeError):
        agents_view.add(2)  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        items_view.add(1000)  # type: ignore[attr-defined]

    # No aliasing: snapshot should not change after mutations; new call reflects change
    apply_world_commands(ctx, [make_set_agent_room(seq=1, agent_id=1, room_id=2)])
    agents_after = views.get_room_agents(1)
    # Old snapshot still contains agent 1
    assert 1 in agents_view
    # New snapshot reflects move
    assert 1 not in agents_after


def test_error_behavior_propagation():
    ctx = WorldContext()
    ctx.register_room(RoomRecord(id=1, label="A"))
    views = WorldViews(ctx)

    # Unknown agent returns None (per WorldContext.get_agent_room semantics)
    assert views.get_agent_room(9999) is None

    # Unknown door should raise KeyError (mirrors WorldContext.is_door_open)
    with pytest.raises(KeyError):
        views.is_door_open(door_id=123)
