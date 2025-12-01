from __future__ import annotations

from dataclasses import dataclass

from backend.sim4.ecs import (
    ECSCommandKind,
    ECSCommand,
    cmd_set_field,
    cmd_set_component,
    cmd_add_component,
    cmd_remove_component,
    cmd_create_entity,
    cmd_destroy_entity,
)


def test_ecs_command_kind_values():
    assert ECSCommandKind.SET_FIELD.value == "set_field"
    assert ECSCommandKind.SET_COMPONENT.value == "set_component"
    assert ECSCommandKind.ADD_COMPONENT.value == "add_component"
    assert ECSCommandKind.REMOVE_COMPONENT.value == "remove_component"
    assert ECSCommandKind.CREATE_ENTITY.value == "create_entity"
    assert ECSCommandKind.DESTROY_ENTITY.value == "destroy_entity"

    # Optional: ensure the enum contains all six
    kinds = {k for k in ECSCommandKind}
    assert {ECSCommandKind.SET_FIELD,
            ECSCommandKind.SET_COMPONENT,
            ECSCommandKind.ADD_COMPONENT,
            ECSCommandKind.REMOVE_COMPONENT,
            ECSCommandKind.CREATE_ENTITY,
            ECSCommandKind.DESTROY_ENTITY} == kinds


@dataclass
class Dummy:
    x: int


def test_cmd_set_field_basic():
    cmd = cmd_set_field(seq=5, entity_id=123, component_type=Dummy, field_name="x", value=42)
    assert cmd.seq == 5
    assert cmd.kind is ECSCommandKind.SET_FIELD
    assert cmd.entity_id == 123
    assert cmd.component_type is Dummy
    assert cmd.field_name == "x"
    assert cmd.field_value == 42
    # Irrelevant fields remain None
    assert cmd.component_instance is None


def test_cmd_set_component_basic():
    comp = Dummy(7)
    cmd = cmd_set_component(seq=1, entity_id=9, component_instance=comp)
    assert cmd.seq == 1
    assert cmd.kind is ECSCommandKind.SET_COMPONENT
    assert cmd.entity_id == 9
    assert cmd.component_type is Dummy
    assert cmd.component_instance is comp
    assert cmd.field_name is None and cmd.field_value is None


def test_cmd_add_component_basic():
    comp = Dummy(3)
    cmd = cmd_add_component(seq=2, entity_id=11, component_instance=comp)
    assert cmd.seq == 2
    assert cmd.kind is ECSCommandKind.ADD_COMPONENT
    assert cmd.entity_id == 11
    assert cmd.component_type is Dummy
    assert cmd.component_instance is comp
    assert cmd.field_name is None and cmd.field_value is None


def test_cmd_remove_component_basic():
    cmd = cmd_remove_component(seq=3, entity_id=15, component_type=Dummy)
    assert cmd.seq == 3
    assert cmd.kind is ECSCommandKind.REMOVE_COMPONENT
    assert cmd.entity_id == 15
    assert cmd.component_type is Dummy
    assert cmd.component_instance is None
    assert cmd.field_name is None and cmd.field_value is None


def test_cmd_create_entity_basic():
    comps = [Dummy(1), Dummy(2)]
    cmd = cmd_create_entity(seq=7, components=comps)
    assert cmd.seq == 7
    assert cmd.kind is ECSCommandKind.CREATE_ENTITY
    assert cmd.entity_id is None
    # We store the components list in component_instance as payload for now (types-only sprint)
    assert cmd.component_instance == comps
    assert cmd.component_type is None
    assert cmd.field_name is None and cmd.field_value is None


def test_cmd_destroy_entity_basic():
    cmd = cmd_destroy_entity(seq=99, entity_id=321)
    assert cmd.seq == 99
    assert cmd.kind is ECSCommandKind.DESTROY_ENTITY
    assert cmd.entity_id == 321
    assert cmd.component_type is None
    assert cmd.component_instance is None
    assert cmd.field_name is None and cmd.field_value is None


def test_seq_ordering_and_comparability():
    c1 = cmd_destroy_entity(1, 10)
    c2 = cmd_destroy_entity(2, 11)
    assert c1.seq < c2.seq
