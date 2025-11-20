from __future__ import annotations

"""
Deterministic Emotional Arc Engine (Sprint 6, EA-1)
- Pure, read-only mapping from telemetry → AgentEmotionState
- No randomness, no LLM, lives above the seam
"""
from typing import Optional, TYPE_CHECKING, Any

# Avoid circular import at runtime: only import types for typing
if TYPE_CHECKING:  # pragma: no cover - typing only
    from loopforge.reporting import AgentDayStats
from loopforge.schema.types import AgentReflectionState, AgentEmotionState
from loopforge.attribution import BeliefAttribution


def derive_emotion_state(
    *,
    agent_day_stats: AgentDayStats,
    reflection_state: Optional[AgentReflectionState],
    attribution: Optional[BeliefAttribution],
) -> AgentEmotionState:
    """Derive a compact emotion snapshot deterministically.

    Inputs considered:
    - agent_day_stats.avg_stress (float in [0,1])
    - reflection_state.stress_trend if provided, else "unknown"
    - attribution.cause if provided, else "unknown"

    Returns an AgentEmotionState with fields:
    - mood ∈ {"calm","uneasy","tense","brittle"}
    - certainty ∈ {"confident","uncertain","doubtful"}
    - energy ∈ {"drained","steady","wired"}
    """
    # Extract primitives with safe fallbacks
    s = float(getattr(agent_day_stats, "avg_stress", 0.0) or 0.0)
    trend = (
        getattr(reflection_state, "stress_trend", "unknown")
        if reflection_state is not None
        else "unknown"
    )
    cause = (
        getattr(attribution, "cause", "unknown")
        if attribution is not None
        else "unknown"
    )

    # 2.1 Mood rules (hard-coded bands + trend influence)
    if s < 0.15 and trend in {"falling", "flat", "unknown"}:
        mood = "calm"
    elif 0.15 <= s < 0.35:
        if trend == "rising":
            mood = "tense"
        else:
            mood = "uneasy"
    else:  # s >= 0.35
        if trend == "rising":
            mood = "brittle"
        else:
            mood = "tense"

    # 2.2 Certainty rules using cause + trend
    if cause in {"system", "supervisor", "self"} and trend in {"rising", "falling", "flat"}:
        certainty = "confident"
    elif cause == "random":
        certainty = "uncertain" if trend == "falling" else "doubtful"
    else:  # cause unknown or trend unknown
        certainty = "uncertain"

    # 2.3 Energy rules using stress only
    if s < 0.10:
        energy = "drained"
    elif s < 0.40:
        energy = "steady"
    else:
        energy = "wired"

    return AgentEmotionState(mood=mood, certainty=certainty, energy=energy)
