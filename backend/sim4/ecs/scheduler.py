# sim4/ecs/scheduler.py

import time
from collections import defaultdict
from typing import Callable, Dict, List

from ..ecs.entity import EntityAllocator, EntityID
from ..ecs.storage import ArchetypeStorage
from ..ecs.archetype import signature_of
from ..ecs.query import Query

from ..runtime.logger import RuntimeLogger
from ..runtime.event_bus import EventBus


class World:
    """
    Era III–V ECS World
    ====================
    - Manages archetypes (SOA storage)
    - Allocates stable EntityIDs
    - Runs system phases deterministically
    - Integrates:
        ✓ RuntimeLogger
        ✓ EventBus (emit/defer/flush)
        ✓ System-level profiling
    """

    def __init__(self, logger: RuntimeLogger = None, event_bus: EventBus = None):
        # Entity allocation
        self.entity_alloc = EntityAllocator()

        # Archetype signatures -> storage
        self.archetypes: Dict[tuple, ArchetypeStorage] = {}

        # Phases → system function list
        self.system_phases: Dict[str, List[Callable]] = defaultdict(list)

        # Phase order (Era V canonical)
        self.phase_order = [
            "perception",
            "cognition",
            "emotion",
            "intention",
            "action",
            "movement",
            "resolution",
        ]

        # Runtime debugging
        self.logger = logger or RuntimeLogger(enabled=False)
        self.event_bus = event_bus or EventBus()

        # Simulation tick counter
        self.tick = 0

    # ------------------------------------------------------------
    # ENTITY CREATION
    # ------------------------------------------------------------
    def create_entity(self, **components):
        """
        Example:
            world.create_entity(
                Transform=Transform(...),
                Velocity=Velocity(...),
                EmotionalState=EmotionalState(...)
            )
        """
        ent_id = self.entity_alloc.create()

        comp_dict = {ctype: c for ctype, c in components.items()}
        comp_dict["_id"] = ent_id

        self._insert_into_archetype(ent_id, comp_dict)

        self.logger.log(
            tick=self.tick,
            event="ENTITY",
            message=f"Created {ent_id}",
            payload={"components": list(comp_dict.keys())},
        )

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
    # SYSTEM REGISTRATION
    # ------------------------------------------------------------
    def add_system(self, phase: str, system_func: Callable):
        if phase not in self.phase_order:
            raise ValueError(f"Unknown phase '{phase}'")
        self.system_phases[phase].append(system_func)

        self.logger.log(
            tick=self.tick,
            event="SYSTEM",
            message=f"Registered system {system_func.__name__} in phase '{phase}'"
        )

    # ------------------------------------------------------------
    # SYSTEM EXECUTION
    # ------------------------------------------------------------
    def run_phase(self, phase: str, dt: float):
        for system in self.system_phases[phase]:
            start = time.time()

            # ---- Run actual system ----
            system(self, dt)

            end = time.time()

            self.logger.profile(
                system_name=system.__name__,
                dt_start=start,
                dt_end=end
            )

            self.logger.log(
                tick=self.tick,
                event="SYSTEM",
                message=f"{system.__name__} executed",
                payload={"phase": phase, "duration_ms": (end - start) * 1000}
            )

        # Flush deferred events after each phase
        if self.event_bus.deferred_queue:
            flushed = len(self.event_bus.deferred_queue)
            self.event_bus.flush_deferred()
            self.logger.log(
                tick=self.tick,
                event="EVENT",
                message=f"Flushed {flushed} deferred events after phase '{phase}'"
            )

    # ------------------------------------------------------------
    # TICK STEP
    # ------------------------------------------------------------
    def step(self, dt: float):
        self.tick += 1

        self.logger.log(
            tick=self.tick,
            event="TICK",
            message=f"--- Tick {self.tick} start ---"
        )

        for phase in self.phase_order:
            self.run_phase(phase, dt)

        self.logger.log(
            tick=self.tick,
            event="TICK",
            message=f"--- Tick {self.tick} end ---"
        )
