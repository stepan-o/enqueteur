# scheduler.py
from collections import defaultdict
from typing import Callable, Dict, List

from ..ecs.entity import EntityAllocator, EntityID
from ..ecs.storage import ArchetypeStorage
from ..ecs.archetype import signature_of
from ..ecs.query import Query


class World:
    """
    Era III–V ECS World
    - Manages archetypes
    - Allocates entities
    - Runs system phases deterministically
    """

    def __init__(self):
        self.entity_alloc = EntityAllocator()
        self.archetypes: Dict[tuple, ArchetypeStorage] = {}

        # System phases: list of functions
        self.system_phases: Dict[str, List[Callable]] = defaultdict(list)

        # Phase order (Era V)
        self.phase_order = [
            "perception",
            "cognition",
            "emotion",
            "intention",
            "action",
            "movement",
            "resolution",
        ]

    # ------------------------------------------------------------
    # ENTITY CREATION
    # ------------------------------------------------------------
    def create_entity(self, **components):
        """
        Example:
            world.create_entity(
                Transform(...),
                Velocity(...),
                EmotionalState(...)
            )
        """
        ent_id = self.entity_alloc.create()

        # Collect component types
        comp_dict = {type(c): c for c in components.values()}
        comp_dict["_id"] = ent_id

        self._insert_into_archetype(ent_id, comp_dict)
        return ent_id

    def _insert_into_archetype(self, ent_id: EntityID, comp_dict: Dict):
        comp_types = tuple(t for t in comp_dict.keys() if t != "_id")
        sig = signature_of(comp_types)

        if sig not in self.archetypes:
            self.archetypes[sig] = ArchetypeStorage(comp_types)

        self.archetypes[sig].add_entity(ent_id, comp_dict)

    # ------------------------------------------------------------
    # QUERIES
    # ------------------------------------------------------------
    def query(self, *comp_types):
        return Query(self, comp_types)

    # ------------------------------------------------------------
    # SYSTEMS
    # ------------------------------------------------------------
    def add_system(self, phase: str, system_func: Callable):
        if phase not in self.phase_order:
            raise ValueError(f"Unknown phase '{phase}'")
        self.system_phases[phase].append(system_func)

    def run_phase(self, phase: str, dt: float):
        for fn in self.system_phases[phase]:
            fn(self, dt)

    # ------------------------------------------------------------
    # MAIN SIMULATION STEP
    # ------------------------------------------------------------
    def step(self, dt: float):
        for phase in self.phase_order:
            self.run_phase(phase, dt)
