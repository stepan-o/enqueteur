from __future__ import annotations

"""
Deterministic Attribution Engine (Sprint 2):
- Pure function over summary telemetry
- No randomness, no LLM
- Lives above the seam; read-only, does not influence behavior
"""

from typing import Optional, Any, Tuple

from .types import BeliefAttribution


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _confidence_levels(strong: bool, ambiguous: bool = False) -> float:
    # Map flags to fixed confidences per brief
    if ambiguous:
        return 0.2
    return 0.7 if strong else 0.4


def _stress_delta(cur_s: Optional[float], prev_s: Optional[float]) -> Optional[float]:
    if cur_s is None or prev_s is None:
        return None
    try:
        return float(cur_s) - float(prev_s)
    except Exception:
        return None


def derive_belief_attribution(
    agent_day_stats: Any,
    previous_stats: Optional[Any],
    supervisor_activity: float,
    tension: float,  # currently unused for core mapping but accepted for future rules
) -> BeliefAttribution:
    """Compute a BeliefAttribution using deterministic, scalar-only rules.

    Inputs (from stats):
    - guardrail_count, context_count, avg_stress, incidents_nearby
    - previous day's avg_stress (if available)
    - supervisor_activity in [0,1]

    Rule order (per Sprint 2C fix):
    1) If incidents > 0:
       - If context_count > guardrail_count → cause = "self"
       - Else if guardrail_count > 0 AND supervisor_activity >= 0.6 → cause = "supervisor"
       - Else → cause = "system"
       Confidence: strong (0.7) for first/second branch; else 0.4.

    2) If incidents == 0 and stress trend == "rising" (Δ > EPS):
       - If supervisor_activity >= 0.6 → cause = "supervisor" (conf=0.7)
       - Else → cause = "system" (conf=0.7)

    3) If incidents == 0 and stress trend == "falling" (Δ < -EPS):
       - If guardrail_count >= context_count → cause = "system" (conf=0.7)
       - Else → cause = "self" (conf=0.7)

    4) Else (flat/unknown): cause = "random" with confidence = 0.2

    Rationale: one compact sentence stating rule selection.
    """
    g = int(getattr(agent_day_stats, "guardrail_count", 0) or 0)
    c = int(getattr(agent_day_stats, "context_count", 0) or 0)
    s = float(getattr(agent_day_stats, "avg_stress", 0.0) or 0.0)
    incidents = int(getattr(agent_day_stats, "incidents_nearby", 0) or 0)

    prev_s: Optional[float] = None
    if previous_stats is not None:
        try:
            prev_s = float(getattr(previous_stats, "avg_stress", 0.0) or 0.0)
        except Exception:
            prev_s = None

    delta = _stress_delta(s, prev_s)
    sup_active = float(supervisor_activity or 0.0)
    high_sup = sup_active >= 0.6

    # Classify stress trend with explicit EPS band
    EPS = 0.01
    if prev_s is None or delta is None:
        trend = "unknown"
    else:
        if delta < -EPS:
            trend = "falling"
        elif delta > EPS:
            trend = "rising"
        else:
            trend = "flat"

    # 1) Incidents present
    if incidents > 0:
        if c > g:
            cause = "self"
            conf = _confidence_levels(strong=True)
            rationale = "Incidents occurred while context choices dominated."
            return BeliefAttribution(cause=cause, confidence=_clamp01(conf), rationale=rationale)
        if g > 0 and high_sup:
            cause = "supervisor"
            conf = _confidence_levels(strong=True)
            rationale = "Incidents under protocol with active supervision." \
                        ""
            return BeliefAttribution(cause=cause, confidence=_clamp01(conf), rationale=rationale)
        cause = "system"
        conf = _confidence_levels(strong=False)
        rationale = "Incidents with no clear agent or supervisor skew."
        return BeliefAttribution(cause=cause, confidence=_clamp01(conf), rationale=rationale)

    # 2) No incidents & stress rising
    if incidents == 0 and trend == "rising":
        cause = "supervisor" if high_sup else "system"
        conf = _confidence_levels(strong=True)
        rationale = "Stress rose without incidents; supervisor/system pressure felt."
        return BeliefAttribution(cause=cause, confidence=_clamp01(conf), rationale=rationale)

    # 3) No incidents & stress falling
    if incidents == 0 and trend == "falling":
        if g >= c:
            cause = "system"
            rationale = "Stress fell without incidents; guardrail-heavy day suggests system stability."
        else:
            cause = "self"
            rationale = "Stress fell without incidents; context-heavy day suggests self-driven improvement."
        conf = _confidence_levels(strong=True)
        return BeliefAttribution(cause=cause, confidence=_clamp01(conf), rationale=rationale)

    # 4) Flat/unknown → random
    cause = "random"
    conf = 0.2
    rationale = "No incidents and no clear stress trend; agent attributes outcome to chance."
    return BeliefAttribution(cause=cause, confidence=_clamp01(conf), rationale=rationale)
