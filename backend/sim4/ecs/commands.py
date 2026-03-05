from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any, List

from .entity import EntityID


class ECSCommandKind(str, Enum):
    """
    Enum-like kind for ECS mutation commands.

    Stable string values are part of the cross-language contract.
    """

    SET_FIELD = "set_field"
    SET_COMPONENT = "set_component"
    ADD_COMPONENT = "add_component"
    REMOVE_COMPONENT = "remove_component"
    CREATE_ENTITY = "create_entity"
    DESTROY_ENTITY = "destroy_entity"


@dataclass(frozen=True)
class ECSCommand:
    """
    Canonical ECS mutation command for Sim4.

    Fields and usage per kind (Python prototype; SimX/Rust-ready):
    - seq: global, monotonic sequence number within a tick.
    - kind: what this command does (see ECSCommandKind).
    - entity_id: target entity, if applicable (not used for CREATE_ENTITY).
    - component_type: Python component class being referenced, if applicable.
    - component_type_code: reserved numeric type code for SimX/Rust (unused in Python for now).
    - component_instance: full component instance (for SET_COMPONENT/ADD_COMPONENT), if applicable.
    - field_name: component field name (for SET_FIELD).
    - value: new field value (for SET_FIELD).
    - archetype_code: reserved numeric archetype code for SimX/Rust (unused in Python for now).
    - initial_components: list of component instances for CREATE_ENTITY (canonical payload in Sim4 Python prototype).
    """

    seq: int
    kind: ECSCommandKind

    entity_id: Optional[EntityID] = None
    component_type: Optional[type] = None
    component_type_code: Optional[int] = None
    component_instance: Optional[object] = None
    field_name: Optional[str] = None
    value: Optional[object] = None
    archetype_code: Optional[int] = None
    initial_components: Optional[List[object]] = None


def cmd_set_field(
    seq: int,
    entity_id: EntityID,
    component_type: type,
    field_name: str,
    value: Any,
) -> ECSCommand:
    return ECSCommand(
        seq=seq,
        kind=ECSCommandKind.SET_FIELD,
        entity_id=entity_id,
        component_type=component_type,
        field_name=field_name,
        value=value,
    )


def cmd_set_component(
    seq: int,
    entity_id: EntityID,
    component_instance: object,
) -> ECSCommand:
    return ECSCommand(
        seq=seq,
        kind=ECSCommandKind.SET_COMPONENT,
        entity_id=entity_id,
        component_type=type(component_instance),
        component_instance=component_instance,
    )


def cmd_add_component(
    seq: int,
    entity_id: EntityID,
    component_instance: object,
) -> ECSCommand:
    return ECSCommand(
        seq=seq,
        kind=ECSCommandKind.ADD_COMPONENT,
        entity_id=entity_id,
        component_type=type(component_instance),
        component_instance=component_instance,
    )


def cmd_remove_component(
    seq: int,
    entity_id: EntityID,
    component_type: type,
) -> ECSCommand:
    return ECSCommand(
        seq=seq,
        kind=ECSCommandKind.REMOVE_COMPONENT,
        entity_id=entity_id,
        component_type=component_type,
    )


def cmd_create_entity(
    seq: int,
    components: Optional[List[object]] = None,
) -> ECSCommand:
    """
    For CREATE_ENTITY, entity_id is None; `components` holds an optional list
    of initial component instances. In Sim4 Python prototype this list is stored
    in `initial_components` (canonical) and consumed by ECSWorld._apply_create_entity.
    component_type_code/archetype_code are reserved for future SimX/Rust usage.
    """
    return ECSCommand(
        seq=seq,
        kind=ECSCommandKind.CREATE_ENTITY,
        entity_id=None,
        initial_components=components,
    )


def cmd_destroy_entity(
    seq: int,
    entity_id: EntityID,
) -> ECSCommand:
    return ECSCommand(
        seq=seq,
        kind=ECSCommandKind.DESTROY_ENTITY,
        entity_id=entity_id,
    )
