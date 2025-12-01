from __future__ import annotations

"""
Phase C system skeleton — CognitivePreprocessor.

Skeleton only: defines run(ctx) and iterates over a deterministic query
without mutating ECS state.
"""

from .base import SystemContext
from ..query import QuerySignature
from ..components.belief import BeliefGraphSubstrate, AgentInferenceState
from ..components.perception import PerceptionSubstrate, SalienceState


class CognitivePreprocessor:
    """
    Phase C: CognitivePreprocessor (skeleton).

    Reads belief + perception substrates; writes updated belief/inference state.
    """

    def run(self, ctx: SystemContext) -> None:
        signature = QuerySignature(
            read=(
                BeliefGraphSubstrate,
                AgentInferenceState,
                PerceptionSubstrate,
                SalienceState,
            ),
            write=(),
        )
        result = ctx.world.query(signature)

        for row in result:
            # TODO[SYS]: Implement belief update logic later.
            _ = row.entity
