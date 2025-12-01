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

    - seq: global, monotonic sequence number within a tick.
    - kind: what this command does (see ECSCommandKind).
    - entity_id: target entity, if applicable.
    - component_type: type of component being referenced, if applicable.
    - component_instance: full component instance (for add/set), if applicable.
    - field_name: component field name (for SET_FIELD).
    - field_value: new field value (for SET_FIELD).
    """

    seq: int
    kind: ECSCommandKind

    entity_id: Optional[EntityID] = None
    component_type: Optional[type] = None
    component_instance: Optional[object] = None
    field_name: Optional[str] = None
    field_value: Optional[object] = None


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
        field_value=value,
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
    For CREATE_ENTITY, entity_id is None; components holds an optional list
    of initial component instances. Components will be interpreted by ECSWorld
    later (in a different sprint).
    """
    # For create, capture the first component instance when present for potential
    # ease of inspection; ECSWorld will consume the list itself later. We keep
    # component_type/instance None to avoid overloading semantics here.
    return ECSCommand(
        seq=seq,
        kind=ECSCommandKind.CREATE_ENTITY,
        entity_id=None,
        component_instance=components,  # store the list in component_instance field as a payload
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
