from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.sim4.ecs import (
    ECSWorld,
    cmd_set_component,
    cmd_set_field,
)


@dataclass
class DummyComponent:
    x: int


def test_apply_commands_set_component_replaces_existing():
    world = ECSWorld()
    e = world.create_entity()

    # Attach initial component via normal API
    world.add_component(e, DummyComponent(x=1))

    # Issue SET_COMPONENT to replace the instance
    cmd = cmd_set_component(seq=1, entity_id=e, component_instance=DummyComponent(x=10))
    world.apply_commands([cmd])

    comp = world.get_component(e, DummyComponent)
    assert comp is not None
    assert comp.x == 10


def test_apply_commands_set_field_updates_component_field():
    world = ECSWorld()
    e = world.create_entity()
    world.add_component(e, DummyComponent(x=10))

    cmd = cmd_set_field(
        seq=1,
        entity_id=e,
        component_type=DummyComponent,
        field_name="x",
        value=42,
    )

    world.apply_commands([cmd])

    comp = world.get_component(e, DummyComponent)
    assert comp is not None
    assert comp.x == 42


def test_apply_commands_respects_seq_ordering():
    world = ECSWorld()
    e = world.create_entity()
    world.add_component(e, DummyComponent(x=0))

    # Intentionally out-of-order seq numbers
    cmd_late = cmd_set_field(
        seq=2,
        entity_id=e,
        component_type=DummyComponent,
        field_name="x",
        value=10,
    )
    cmd_early = cmd_set_field(
        seq=1,
        entity_id=e,
        component_type=DummyComponent,
        field_name="x",
        value=5,
    )

    world.apply_commands([cmd_late, cmd_early])

    comp = world.get_component(e, DummyComponent)
    assert comp is not None
    # seq=1 applied first (x=5), then seq=2 (x=10)
    assert comp.x == 10
