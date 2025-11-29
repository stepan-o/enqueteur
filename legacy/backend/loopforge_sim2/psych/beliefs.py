from __future__ import annotations

"""
Deterministic, read-only belief derivation functions.

- No randomness
- Pure functions over summary telemetry
- Lives above the seam; does not influence behavior
"""

from dataclasses import dataclass
from typing import Optional, Any

from loopforge.schema.types import BeliefState


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _step(value: float, delta: float) -> float:
    return _clamp01(float(value) + float(delta))


def derive_belief_state(
    agent_day_stats: Any,
    previous_stats: Optional[Any],
    supervisor_activity: float,
    tension: float,
) -> BeliefState:
    """Compute a BeliefState from day stats and environment-level cues.

    Rules (±0.05 steps; all clamped to 0..1):
    - Guardrail faith:
      * increase if guardrail_count > context_count and incidents == 0
      * decrease if guardrail_count > context_count and incidents > 0
      * increase slightly if stress decreased relative to previous day
    - Self-efficacy:
      * increase if context_count > guardrail_count and incidents == 0
      * decrease if context_count > guardrail_count and incidents > 0
      * increase slightly if avg_stress < previous_avg_stress
    - Supervisor trust:
      * decrease if supervisor_activity is high AND stress increased
      * increase if supervisor_activity is high AND stress decreased
    - World predictability:
      * decrease if incidents > 0
      * increase if day had both low tension AND stress dropped
    - Incident attribution (priority order):
      * if incidents > 2 → "random"
      * elif incidents == 0 → "world"
      * elif context_count > guardrail_count → "self"
      * elif guardrail_count > context_count → "supervisor"
      * else → "world"
    """
    # Baseline
    supervisor_trust = 0.5
    guardrail_faith = 0.5
    self_efficacy = 0.5
    world_predictability = 0.5

    g = int(getattr(agent_day_stats, "guardrail_count", 0) or 0)
    c = int(getattr(agent_day_stats, "context_count", 0) or 0)
    s = float(getattr(agent_day_stats, "avg_stress", 0.0) or 0.0)
    incidents = int(getattr(agent_day_stats, "incidents_nearby", 0) or 0)

    prev_s = None
    if previous_stats is not None:
        try:
            prev_s = float(getattr(previous_stats, "avg_stress", 0.0) or 0.0)
        except Exception:
            prev_s = None

    # Guardrail faith adjustments
    if g > c and incidents == 0:
        guardrail_faith = _step(guardrail_faith, +0.05)
    if g > c and incidents > 0:
        guardrail_faith = _step(guardrail_faith, -0.05)
    if prev_s is not None and s < prev_s:
        guardrail_faith = _step(guardrail_faith, +0.05)

    # Self-efficacy adjustments
    if c > g and incidents == 0:
        self_efficacy = _step(self_efficacy, +0.05)
    if c > g and incidents > 0:
        self_efficacy = _step(self_efficacy, -0.05)
    if prev_s is not None and s < prev_s:
        self_efficacy = _step(self_efficacy, +0.05)

    # Supervisor trust adjustments (consider supervisor_activity high if >= 0.6)
    sup_active = float(supervisor_activity or 0.0)
    high_sup = sup_active >= 0.6
    if prev_s is not None and high_sup:
        if s > prev_s:
            supervisor_trust = _step(supervisor_trust, -0.05)
        elif s < prev_s:
            supervisor_trust = _step(supervisor_trust, +0.05)

    # World predictability adjustments
    if incidents > 0:
        world_predictability = _step(world_predictability, -0.05)
    if prev_s is not None and (tension or 0.0) < 0.3 and s < prev_s:
        world_predictability = _step(world_predictability, +0.05)

    # Incident attribution
    if incidents > 2:
        attribution = "random"
    elif incidents == 0:
        attribution = "world"
    elif c > g:
        attribution = "self"
    elif g > c:
        attribution = "supervisor"
    else:
        attribution = "world"

    return BeliefState(
        supervisor_trust=_clamp01(supervisor_trust),
        guardrail_faith=_clamp01(guardrail_faith),
        self_efficacy=_clamp01(self_efficacy),
        world_predictability=_clamp01(world_predictability),
        incident_attribution=attribution,
    )
