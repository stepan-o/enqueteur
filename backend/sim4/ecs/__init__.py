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

__all__ = [
    "EntityID",
    "EntityAllocator",
    "ArchetypeSignature",
    "ArchetypeRegistry",
    "ArchetypeStorage",
    "ECSWorld",
    "QuerySignature",
    "QueryResult",
]
