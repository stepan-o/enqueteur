"""
Exports for ECS core (Sprints 1.1–1.4):

- EntityID and EntityAllocator (S1.1)
- ArchetypeSignature and ArchetypeRegistry (S1.2)
- ArchetypeStorage (S1.3)
- ECSWorld, QuerySignature, QueryResult (S1.4)

Keep this module minimal and layer‑pure per SOT-SIM4-ECS-CORE.
"""

from .entity import EntityID, EntityAllocator
from .archetype import ArchetypeSignature, ArchetypeRegistry
from .storage import ArchetypeStorage
from .world import ECSWorld
from .query import QuerySignature, QueryResult
from .commands import (
    ECSCommandKind,
    ECSCommand,
    cmd_set_field,
    cmd_set_component,
    cmd_add_component,
    cmd_remove_component,
    cmd_create_entity,
    cmd_destroy_entity,
)

__all__ = [
    "EntityID",
    "EntityAllocator",
    "ArchetypeSignature",
    "ArchetypeRegistry",
    "ArchetypeStorage",
    "ECSWorld",
    "QuerySignature",
    "QueryResult",
    "ECSCommandKind",
    "ECSCommand",
    "cmd_set_field",
    "cmd_set_component",
    "cmd_add_component",
    "cmd_remove_component",
    "cmd_create_entity",
    "cmd_destroy_entity",
]
