"""
Exports for ECS core (Sprint 1.1): EntityID and EntityAllocator.

Keep this module minimal and layer‑pure per SOT-SIM4-ECS-CORE.
"""

from .entity import EntityID, EntityAllocator

__all__ = [
    "EntityID",
    "EntityAllocator",
]
