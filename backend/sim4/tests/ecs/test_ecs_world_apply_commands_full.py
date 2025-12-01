from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.sim4.ecs import (
    ECSWorld,
    cmd_set_field,
    cmd_add_component,
    cmd_create_entity,
    cmd_destroy_entity,
    cmd_set_component,
    cmd_remove_component,
)


@dataclass
class CompA:
    x: int


@dataclass
class CompB:
    y: int


def test_full_lifecycle_create_add_set_destroy():
    world = ECSWorld()

    # 1) Create entity with initial CompA
    create_cmd = cmd_create_entity(seq=1, components=[CompA(x=1)])
    world.apply_commands([create_cmd])

    # obtain created entity id (only one exists)
    ids = list(world.iter_entity_ids())
    assert len(ids) == 1
    e = ids[0]

    # Before any mutations, CompA.x should be 1 and CompB absent
    a = world.get_component(e, CompA)
    assert a is not None and a.x == 1
    assert world.get_component(e, CompB) is None

    # 2) Add CompB, set field, then destroy
    add_b = cmd_add_component(seq=2, entity_id=e, component_instance=CompB(y=2))
    set_b_y = cmd_set_field(
        seq=3, entity_id=e, component_type=CompB, field_name="y", value=5
    )
    destroy = cmd_destroy_entity(seq=4, entity_id=e)

    world.apply_commands([add_b, set_b_y])

    # Verify state prior to destruction
    b = world.get_component(e, CompB)
    assert b is not None and b.y == 5

    # Now destroy
    world.apply_commands([destroy])

    # Entity should be gone
    assert not world.has_entity(e)
    assert world.get_component(e, CompA) is None
    assert world.get_component(e, CompB) is None


def test_add_component_moves_entity_and_exposes_both_components():
    world = ECSWorld()
    e = world.create_entity()
    world.add_component(e, CompA(x=1))

    # Add CompB via command
    cmd = cmd_add_component(seq=1, entity_id=e, component_instance=CompB(y=2))
    world.apply_commands([cmd])

    a = world.get_component(e, CompA)
    b = world.get_component(e, CompB)

    assert a is not None and a.x == 1
    assert b is not None and b.y == 2


def test_apply_commands_is_deterministic_with_seq_order():
    world1 = ECSWorld()
    world2 = ECSWorld()

    e1 = world1.create_entity()
    world1.add_component(e1, CompA(x=0))

    e2 = world2.create_entity()
    world2.add_component(e2, CompA(x=0))

    cmds = [
        cmd_set_field(seq=2, entity_id=e1, component_type=CompA, field_name="x", value=10),
        cmd_set_field(seq=1, entity_id=e1, component_type=CompA, field_name="x", value=5),
    ]

    # Different input ordering of the same commands
    world1.apply_commands(cmds)
    world2.apply_commands(list(reversed(cmds)))

    comp1 = world1.get_component(e1, CompA)
    comp2 = world2.get_component(e2, CompA)
    assert comp1 is not None and comp2 is not None
    assert comp1.x == comp2.x == 10


def test_error_and_noop_semantics():
    world = ECSWorld()

    # Destroy non-existent entity -> no-op
    world.apply_commands([cmd_destroy_entity(seq=1, entity_id=999)])

    # Create a real entity
    e = world.create_entity()
    world.add_component(e, CompA(x=1))

    # ADD/SET on non-existent entity -> ValueError
    with pytest.raises(ValueError):
        world.apply_commands([cmd_add_component(seq=2, entity_id=777, component_instance=CompB(1))])
    with pytest.raises(ValueError):
        world.apply_commands([cmd_set_component(seq=3, entity_id=777, component_instance=CompB(2))])

    # REMOVE on non-existent entity -> ValueError
    with pytest.raises(ValueError):
        world.apply_commands([cmd_remove_component(seq=4, entity_id=555, component_type=CompB)])

    # REMOVE missing component on existing entity -> no-op
    world.apply_commands([cmd_remove_component(seq=5, entity_id=e, component_type=CompB)])
