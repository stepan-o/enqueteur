from __future__ import annotations

"""
Phase C system skeleton — PlanResolutionSystem.

Skeleton only: defines run(ctx) and queries relevant planning substrates
plus embodiment/path state. No ECS mutations are made.
"""

from .base import SystemContext
from ..components.motive_plan import MotiveSubstrate, PlanLayerSubstrate
from ..components.embodiment import Transform, RoomPresence, PathState


class PlanResolutionSystem:
    """
    Phase C: PlanResolutionSystem (skeleton).

    Maintains and revises plans based on motives and feasibility.
    """

    def run(self, ctx: SystemContext) -> None:
        result = ctx.world.query(
            (MotiveSubstrate, PlanLayerSubstrate, Transform, RoomPresence, PathState)
        )
        for eid, _comps in result:
            # TODO[SYS]: Implement plan resolution logic later.
            _ = eid
