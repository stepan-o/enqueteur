"""Sim4 runtime package public API (Sprint 6/8.1).

Stable, minimal surface for upper layers (engine, snapshot, narrative):

from backend.sim4.runtime import tick, TickClock, TickResult, RuntimeEvent

Notes:
- Do not expand this surface without a SOT-backed decision; keep imports minimal
  and layer-pure (SOP-100).
"""

from .clock import TickClock
from .tick import tick, TickResult
from .events import RuntimeEvent
from .narrative_context import (
    NarrativeBudget,
    NarrativeTickContext,
    NarrativeTickOutput,
    SubstrateSuggestion,
    StoryFragment,
    MemoryUpdate,
    NarrativeEpisodeContext,
    NarrativeEpisodeOutput,
    NarrativeUICallContext,
    NarrativeUIText,
)

__all__ = [
    "TickClock",
    "tick",
    "TickResult",
    "RuntimeEvent",
    # Narrative DTOs (runtime-owned)
    "NarrativeBudget",
    "NarrativeTickContext",
    "NarrativeTickOutput",
    "SubstrateSuggestion",
    "StoryFragment",
    "MemoryUpdate",
    "NarrativeEpisodeContext",
    "NarrativeEpisodeOutput",
    "NarrativeUICallContext",
    "NarrativeUIText",
]
