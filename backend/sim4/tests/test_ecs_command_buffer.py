from __future__ import annotations

from dataclasses import dataclass

from backend.sim4.ecs.systems.base import ECSCommandBuffer
from backend.sim4.ecs import ECSCommandKind


@dataclass
class CompA:
    x: int


@dataclass
class CompB:
    y: int


def test_command_buffer_seq_and_len():
    buf = ECSCommandBuffer()

    buf.create_entity()
    buf.destroy_entity(entity_id=1)
    buf.add_component(entity_id=1, component_instance=CompA(x=10))
    buf.set_field(entity_id=1, component_type=CompA, field_name="x", value=20)

    cmds = buf.commands

    assert len(cmds) == 4
    assert [c.seq for c in cmds] == [0, 1, 2, 3]


def test_set_field_creates_proper_command():
    buf = ECSCommandBuffer()
    buf.set_field(entity_id=42, component_type=CompA, field_name="x", value=99)

    (cmd,) = buf.commands
    assert cmd.kind is ECSCommandKind.SET_FIELD
    assert cmd.entity_id == 42
    assert cmd.component_type is CompA
    assert cmd.field_name == "x"
    assert cmd.value == 99


def test_add_component_creates_proper_command():
    buf = ECSCommandBuffer()
    comp = CompB(y=5)
    buf.add_component(entity_id=7, component_instance=comp)

    (cmd,) = buf.commands
    assert cmd.kind is ECSCommandKind.ADD_COMPONENT
    assert cmd.entity_id == 7
    assert cmd.component_instance is comp


def test_create_entity_with_and_without_components():
    buf = ECSCommandBuffer()

    buf.create_entity()
    buf.create_entity(components=[CompA(x=1), CompB(y=2)])

    cmds = buf.commands
    assert cmds[0].kind is ECSCommandKind.CREATE_ENTITY
    assert cmds[0].initial_components is None

    assert cmds[1].kind is ECSCommandKind.CREATE_ENTITY
    assert isinstance(cmds[1].initial_components, list)
    assert len(cmds[1].initial_components) == 2


def test_destroy_entity_command():
    buf = ECSCommandBuffer()
    buf.destroy_entity(entity_id=99)

    (cmd,) = buf.commands
    assert cmd.kind is ECSCommandKind.DESTROY_ENTITY
    assert cmd.entity_id == 99


def test_commands_property_returns_copy():
    buf = ECSCommandBuffer()
    buf.create_entity()

    cmds1 = buf.commands
    cmds2 = buf.commands

    assert cmds1 is not cmds2
    assert cmds1[0] is cmds2[0]

    # Mutating cmds1 should not affect internal buffer
    cmds1.pop()
    assert len(buf.commands) == 1
