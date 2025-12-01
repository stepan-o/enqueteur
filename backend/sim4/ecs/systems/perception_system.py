from __future__ import annotations

"""
Phase B system skeletons — PerceptionSystem.

Skeleton only: defines a run(ctx) method that performs a deterministic query
for relevant components and iterates rows without mutating ECS state.

Per SOT-SIM4-ECS-SYSTEMS, this system will eventually read embodiment and
profile substrates and write perception substrates. For now, we simply
wire the query and no-op over results.
"""

from .base import SystemContext
from ..query import QuerySignature
from ..components.embodiment import Transform, RoomPresence
from ..components.identity import ProfileTraits
from ..components.perception import (
    PerceptionSubstrate,
    AttentionSlots,
    SalienceState,
)


class PerceptionSystem:
    """
    Phase B: PerceptionSystem (skeleton).

    Reads Transform/RoomPresence/ProfileTraits and writes perception substrates.
    """

    def run(self, ctx: SystemContext) -> None:
        # Query for entities that have the expected input/output substrates.
        # Our query API accepts a tuple of component types and yields
        # (entity_id, (components...)) in deterministic order.
        signature = QuerySignature(
            read=(
                Transform,
                RoomPresence,
                ProfileTraits,
                PerceptionSubstrate,
                AttentionSlots,
                SalienceState,
            ),
            write=(),
        )
        result = ctx.world.query(signature)

        for row in result:
            # TODO[SYS]: Implement perception logic in later sprint.
            _ = row.entity
