from __future__ import annotations

"""
Phase D system skeleton — InteractionResolutionSystem.

Skeleton only: resolves non-movement interactions into InteractionIntent +
ActionState. Currently performs a deterministic query and iterates without
mutating ECS state.
"""

from .base import SystemContext
from ..components.intent_action import InteractionIntent, SanitizedIntent, ActionState
from ..components.embodiment import Transform, RoomPresence
from ..components.inventory import InventorySubstrate, ItemState


class InteractionResolutionSystem:
    """
    Phase D: InteractionResolutionSystem (skeleton).

    Resolves non-movement interactions into InteractionIntent + ActionState.
    """

    def run(self, ctx: SystemContext) -> None:
        result = ctx.world.query(
            (
                SanitizedIntent,
                Transform,
                RoomPresence,
                InventorySubstrate,
                ItemState,
                ActionState,
                InteractionIntent,
            )
        )

        for eid, _comps in result:
            # TODO[SYS]: implement interaction resolution logic later.
            _ = eid
