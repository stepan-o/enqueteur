from __future__ import annotations

"""
Deterministic Narrative Reflection mapper (Sprint 3).

- Pure function over summary telemetry
- No randomness, no LLM
- Lives above the seam; read-only, does not influence behavior
- Produces AgentReflectionState used by narrative renderers for consistency
"""

from typing import Any, Optional

from .types import AgentReflectionState


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def derive_reflection_state(
    agent_stats: Any,
    previous_stats: Optional[Any],
    supervisor_activity: float,
) -> AgentReflectionState:
    """Derive AgentReflectionState from telemetry.

    Rules:
    - Stress trend classification uses EPS=0.01, consistent with Attribution Engine.
      NOTE: This logic must remain consistent with derive_belief_attribution.
        * No previous data -> "unknown"
        * delta >  +EPS -> "rising"
        * delta <  -EPS -> "falling"
        * otherwise       -> "flat"
    - Rulebook reliance: guardrail_count / max(1, guardrail_count + context_count), clamped 0..1.
      This is narrative-only, not behavioral logic.
    - Supervisor presence: passthrough clamp of supervisor_activity (0..1). CLI currently passes 0.0.
    """
    # Gather telemetry
    g = int(getattr(agent_stats, "guardrail_count", 0) or 0)
    c = int(getattr(agent_stats, "context_count", 0) or 0)
    s = float(getattr(agent_stats, "avg_stress", 0.0) or 0.0)

    prev_s: Optional[float] = None
    if previous_stats is not None:
        try:
            prev_s = float(getattr(previous_stats, "avg_stress", 0.0) or 0.0)
        except Exception:
            prev_s = None

    # Stress trend (EPS band consistent with attribution)
    EPS = 0.01
    if prev_s is None:
        stress_trend = "unknown"
    else:
        delta = s - prev_s
        if delta > EPS:
            stress_trend = "rising"
        elif delta < -EPS:
            stress_trend = "falling"
        else:
            stress_trend = "flat"

    # Rulebook reliance (narrative-only ratio)
    total = g + c
    rulebook_reliance = _clamp01((g / total) if total > 0 else 0.0)

    # Supervisor presence (passthrough, clamped)
    supervisor_presence = _clamp01(float(supervisor_activity or 0.0))

    return AgentReflectionState(
        stress_trend=stress_trend,  # type: ignore[arg-type]
        rulebook_reliance=rulebook_reliance,
        supervisor_presence=supervisor_presence,
    )
