from __future__ import annotations

"""
Phase D system skeleton — InventorySystem.

Skeleton only: maintains inventory substrate around interaction intents —
later. For now, performs a deterministic query and iterates without mutating
ECS state.
"""

from .base import SystemContext
from ..components.inventory import InventorySubstrate, ItemState
from ..components.intent_action import InteractionIntent, ActionState


class InventorySystem:
    """
    Phase D: InventorySystem (skeleton).

    Maintains inventory substrate around interaction intents.
    """

    def run(self, ctx: SystemContext) -> None:
        result = ctx.world.query(
            (
                InventorySubstrate,
                ItemState,
                InteractionIntent,
                ActionState,
            )
        )

        for eid, _comps in result:
            # TODO[SYS]: implement inventory update logic later.
            _ = eid
