from __future__ import annotations

"""
Phase D system skeleton — MovementResolutionSystem.

Skeleton only: translates sanitized intents into movement/path updates —
later. For now, performs a deterministic query and iterates without
mutating ECS state.
"""

from .base import SystemContext
from ..components.intent_action import SanitizedIntent, MovementIntent, ActionState
from ..components.embodiment import Transform, RoomPresence, PathState
from ..components.identity import ProfileTraits


class MovementResolutionSystem:
    """
    Phase D: MovementResolutionSystem (skeleton).

    Translates sanitized intents into movement/path updates.
    """

    def run(self, ctx: SystemContext) -> None:
        result = ctx.world.query(
            (
                SanitizedIntent,
                Transform,
                RoomPresence,
                PathState,
                MovementIntent,
                ActionState,
                ProfileTraits,
            )
        )

        for eid, _comps in result:
            # TODO[SYS]: implement movement resolution logic later.
            _ = eid
