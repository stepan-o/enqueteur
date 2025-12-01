from __future__ import annotations

"""
Phase D system skeleton — IntentResolverSystem.

Skeleton only: wires run(ctx) to perform a deterministic query over the
relevant substrates and iterates without mutating ECS state.
"""

from .base import SystemContext
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
        result = ctx.world.query(
            (
                PrimitiveIntent,
                MotiveSubstrate,
                PlanLayerSubstrate,
                DriveState,
                Transform,
                RoomPresence,
                SanitizedIntent,
            )
        )

        for eid, _comps in result:
            # TODO[SYS]: implement intent gating/resolution later.
            _ = eid
