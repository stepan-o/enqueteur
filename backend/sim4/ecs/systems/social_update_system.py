from __future__ import annotations

"""
Phase C system skeleton — SocialUpdateSystem.

Skeleton only: defines run(ctx) and queries social substrates along with
drive/emotion and social belief weights. No ECS mutations are made.
"""

from .base import SystemContext
from ..components.social import (
    SocialSubstrate,
    SocialImpressionState,
    FactionAffinityState,
)
from ..components.drives import DriveState
from ..components.emotion import EmotionFields
from ..components.belief import SocialBeliefWeights


class SocialUpdateSystem:
    """
    Phase C: SocialUpdateSystem (skeleton).

    Updates numeric social substrates (relationships, impressions, factions).
    """

    def run(self, ctx: SystemContext) -> None:
        result = ctx.world.query(
            (
                SocialSubstrate,
                SocialImpressionState,
                FactionAffinityState,
                DriveState,
                EmotionFields,
                SocialBeliefWeights,
            )
        )
        for eid, _comps in result:
            # TODO[SYS]: Implement social update logic later.
            _ = eid
