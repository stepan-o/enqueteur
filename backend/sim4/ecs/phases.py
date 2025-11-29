# backend/sim4/ecs/phases.py

from typing import Callable, Dict, List


class PhaseScheduler:
    """
    AAA Era V system scheduler:
    - Pure orchestration
    - No ECS storage inside
    - No world-specific logic
    - Systems are grouped by phase name
    """

    def __init__(self):
        # phase -> list of system functions
        self.phases: Dict[str, List[Callable]] = {}

        # Default Era V order
        self.phase_order = [
            "perception",
            "cognition",
            "emotion",
            "intention",
            "action",
            "movement",
            "resolution",
        ]

        # Initialize empty lists
        for ph in self.phase_order:
            self.phases[ph] = []


    def add_system(self, phase: str, system_fn: Callable):
        if phase not in self.phases:
            raise ValueError(f"Unknown phase '{phase}'")
        self.phases[phase].append(system_fn)


    def run(self, ecs_world, dt: float):
        """
        Runs all phases, in order, across the ECS world.

        Systems always follow:
            fn(ecs_world, dt)
        """
        for phase in self.phase_order:
            for system_fn in self.phases[phase]:
                system_fn(ecs_world, dt)
