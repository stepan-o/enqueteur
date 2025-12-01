"""
Exports for ECS core (Sprints 1.1–1.3):

- EntityID and EntityAllocator (S1.1)
- ArchetypeSignature and ArchetypeRegistry (S1.2)
- ArchetypeStorage (S1.3)

Keep this module minimal and layer‑pure per SOT-SIM4-ECS-CORE.
"""

from .entity import EntityID, EntityAllocator
from .archetype import ArchetypeSignature, ArchetypeRegistry
from .storage import ArchetypeStorage

__all__ = [
    "EntityID",
    "EntityAllocator",
    "ArchetypeSignature",
    "ArchetypeRegistry",
    "ArchetypeStorage",
]
