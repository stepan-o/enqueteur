# backend/sim4/ecs/scheduler.py (rename later to world.py maybe)

from typing import Dict, Tuple
from .entity import EntityAllocator
from .storage import ArchetypeStorage
from .archetype import signature_of
from .query import Query


class ECSWorld:
    """
    Pure ECS storage layer.
    No phases.
    No system logic.
    """

    def __init__(self, logger=None):
        self.entity_alloc = EntityAllocator()
        self.archetypes: Dict[Tuple, ArchetypeStorage] = {}
        self.logger = logger


    def create_entity(self, **components):
        ent = self.entity_alloc.create()
        comp_dict = {type(c): c for c in components.values()}
        comp_dict["_id"] = ent
        self._insert(ent, comp_dict)
        return ent


    def _insert(self, ent, comp_dict: Dict):
        comp_types = tuple(t for t in comp_dict.keys() if t != "_id")
        sig = signature_of(comp_types)

        if sig not in self.archetypes:
            self.archetypes[sig] = ArchetypeStorage(comp_types)

        self.archetypes[sig].add_entity(ent, comp_dict)


    def query(self, *comp_types):
        return Query(self, comp_types)
