from __future__ import annotations

"""
Phase D system skeleton — IntentResolverSystem.

Skeleton only: wires run(ctx) to perform a deterministic query over the
relevant substrates and iterates without mutating ECS state.
"""

from .base import SystemContext
from ..query import QuerySignature
from ..components.intent_action import PrimitiveIntent, SanitizedIntent
from ..components.motive_plan import MotiveSubstrate, PlanLayerSubstrate
from ..components.drives import DriveState
from ..components.embodiment import Transform, RoomPresence


class IntentResolverSystem:
    """
    Phase D: IntentResolverSystem (skeleton).

    Converts PrimitiveIntent + plans into SanitizedIntent.
    """

    def run(self, ctx: SystemContext) -> None:
        signature = QuerySignature(
            read=(
                PrimitiveIntent,
                MotiveSubstrate,
                PlanLayerSubstrate,
                DriveState,
                Transform,
                RoomPresence,
            ),
            write=(
                SanitizedIntent,
            ),
        )
        result = ctx.world.query(signature)

        for row in result:
            # TODO[SYS]: implement intent gating/resolution later.
            _ = row.entity
