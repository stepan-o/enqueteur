from __future__ import annotations

"""
Phase E system skeleton — ActionExecutionSystem.

Skeleton only: applies movement/interaction results to ECS (and later world
commands). For now, performs a deterministic query and iterates without
mutating ECS state or emitting commands.
"""

from .base import SystemContext
from ..components.intent_action import MovementIntent, InteractionIntent, ActionState
from ..components.embodiment import Transform, RoomPresence, PathState
from ..components.inventory import InventorySubstrate, ItemState


class ActionExecutionSystem:
    """
    Phase E: ActionExecutionSystem (skeleton).

    Applies movement/interaction results to ECS (and later world commands).
    """

    def run(self, ctx: SystemContext) -> None:
        result = ctx.world.query(
            (
                MovementIntent,
                PathState,
                InteractionIntent,
                ActionState,
                Transform,
                RoomPresence,
                InventorySubstrate,
                ItemState,
            )
        )

        for eid, _comps in result:
            # TODO[SYS]: populate ECS/world commands in a later sprint.
            _ = eid
