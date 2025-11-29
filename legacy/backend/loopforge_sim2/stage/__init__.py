"""
Stage layer foundation (Sprint 0.1).

This package defines typed, JSON-serializable models for StageEpisode and a
minimal builder skeleton that assembles a StageEpisode from existing analytics
outputs and narrative pieces.

Behavior note:
- This layer is read-only and does not affect the simulation or CLI behavior.
- Real mapping logic will be added in Sprint 0.2; for now, we focus on types
  and structural wiring with placeholders.

– Junie
"""

from .stage_episode import (
    StageEpisode,
    StageDay,
    StageAgentDayView,
    StageAgentSummary,
    StageNarrativeBlock,
    StageAgentTraits,
)
from .builder import build_stage_episode

__all__ = [
    "StageEpisode",
    "StageDay",
    "StageAgentDayView",
    "StageAgentSummary",
    "StageNarrativeBlock",
    "StageAgentTraits",
    "build_stage_episode",
]
