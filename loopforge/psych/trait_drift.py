from __future__ import annotations
"""
Deterministic Trait Drift Engine (Sprint 9: EA-III)
- Pure, read-only mapping from episode telemetry → per-agent trait snapshot
- No randomness, no LLM, lives above the seam

Traits in snapshot (floats in [0,1]):
- resilience
- caution
- agency
- trust_supervisor
- variance

API:
    derive_trait_snapshot(prev_traits, episode_summary, *, agent_name) -> Dict[str, float]

Notes:
- prev_traits may be None (baseline 0.5s). When provided, we start from those and apply small deltas.
- We clamp to [0,1] after all updates.
- We only read EpisodeSummary/DaySummary; do not mutate them.
"""
from typing import Dict, Optional, List

from loopforge.reporting import EpisodeSummary


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _sign_flips(xs: List[float]) -> int:
    flips = 0
    for a, b in zip(xs, xs[1:]):
        if a == 0 or b == 0:
            continue
        if (a > 0 and b < 0) or (a < 0 and b > 0):
            flips += 1
    return flips


def derive_trait_snapshot(
    prev_traits: Optional[Dict[str, float]],
    episode_summary: EpisodeSummary,
    *,
    agent_name: str,
) -> Dict[str, float]:
    # Baseline values
    base = {
        "resilience": 0.5,
        "caution": 0.5,
        "agency": 0.5,
        "trust_supervisor": 0.5,
        "variance": 0.5,
    }
    # Start from previous or baseline
    traits: Dict[str, float] = dict(base)
    if isinstance(prev_traits, dict):
        for k in base.keys():
            v = prev_traits.get(k)
            if isinstance(v, (int, float)):
                traits[k] = float(v)

    # Pull agent aggregates
    agent = episode_summary.agents.get(agent_name)
    if agent is None:
        # No data; return baseline or prev
        return {k: _clamp01(float(v)) for k, v in traits.items()}

    stress_start = agent.stress_start
    stress_end = agent.stress_end

    # Build blame timeline from days
    blame_timeline: List[str] = []
    for d in episode_summary.days:
        attr = (getattr(d, "belief_attributions", {}) or {}).get(agent_name)
        cause = getattr(attr, "cause", None) if attr is not None else None
        blame_timeline.append(cause or "unknown")

    # Belief drift (supervisor trust) from beliefs on day 0 vs last
    belief_start = None
    belief_end = None
    if episode_summary.days:
        d0 = episode_summary.days[0]
        dn = episode_summary.days[-1]
        b0 = (getattr(d0, "beliefs", {}) or {}).get(agent_name)
        bn = (getattr(dn, "beliefs", {}) or {}).get(agent_name)
        try:
            belief_start = float(getattr(b0, "supervisor_trust", 0.5)) if b0 is not None else None
        except Exception:
            belief_start = None
        try:
            belief_end = float(getattr(bn, "supervisor_trust", 0.5)) if bn is not None else None
        except Exception:
            belief_end = None

    # Emotional and supervisor patterns from story arc (when available)
    emotional_color = None
    supervisor_pattern = None
    try:
        arc = getattr(episode_summary, "story_arc", None)
        if arc is not None:
            emotional_color = getattr(arc, "emotional_color", None)
            supervisor_pattern = getattr(arc, "supervisor_pattern", None)
    except Exception:
        emotional_color = None
        supervisor_pattern = None

    # Derived helper signals
    # Stress delta and monotonicity across days for this agent (use day-wise avg_stress deltas)
    per_day_stress: List[float] = []
    for d in episode_summary.days:
        s = getattr(d.agent_stats.get(agent_name), "avg_stress", None) if agent_name in d.agent_stats else None
        per_day_stress.append(0.0 if s is None else float(s))
    deltas = [b - a for a, b in zip(per_day_stress, per_day_stress[1:])]
    monotonic_falling = all(x < -0.01 for x in deltas) if deltas else False

    # Guardrail reliance ratio over the episode
    total = float(agent.guardrail_total + agent.context_total)
    guardrail_ratio = (float(agent.guardrail_total) / total) if total > 0 else 0.0

    # Dominant attribution category across days
    from collections import Counter

    counts = Counter([c for c in blame_timeline if isinstance(c, str)])
    dominant = None
    if counts:
        dominant = max(counts, key=counts.get)

    # Distinct attribution categories for variance
    distinct = len(set([c for c in blame_timeline if isinstance(c, str)]))

    # ------------- Apply deterministic deltas ----------------
    # Resilience: stress falling +0.03; rising -0.03; emotional modifiers
    if isinstance(stress_start, (int, float)) and isinstance(stress_end, (int, float)):
        if stress_end < stress_start - 0.01:
            traits["resilience"] += 0.03
        elif stress_end > stress_start + 0.01:
            traits["resilience"] -= 0.03
    if isinstance(emotional_color, str):
        if "exhaustion" in emotional_color:
            # Exhaustion should outweigh small improvements from falling stress
            # Net effect with typical -/+ 0.03 stress delta should not increase resilience
            traits["resilience"] -= 0.04
        if "wired_to_calm" in emotional_color:
            traits["resilience"] += 0.02

    # Caution: guardrail-heavy +0.03; random-dominant +0.02; system-dominant -0.02
    if guardrail_ratio >= 0.7:
        traits["caution"] += 0.03
    if dominant == "random":
        traits["caution"] += 0.02
    if dominant == "system":
        traits["caution"] -= 0.02

    # Agency: self-dominant +0.05; supervisor-dominant -0.03; monotonic falling stress +0.02
    if dominant == "self":
        traits["agency"] += 0.05
    if dominant == "supervisor":
        traits["agency"] -= 0.03
    if monotonic_falling:
        traits["agency"] += 0.02

    # Trust Supervisor: carry over belief drift scaled by 0.5; supervisor presence/pattern tweaks
    if isinstance(belief_start, float) and isinstance(belief_end, float):
        traits["trust_supervisor"] += 0.5 * (belief_end - belief_start)
    # supervisor presence via reflection_states mean (approximate using story_arc supervisor_pattern)
    if isinstance(supervisor_pattern, str):
        if supervisor_pattern == "looming":
            traits["trust_supervisor"] += 0.03
        elif supervisor_pattern == "background":
            traits["trust_supervisor"] += 0.02
        elif supervisor_pattern == "hands_off":
            traits["trust_supervisor"] -= 0.02

    # Variance: distinct categories / 4 baseline; bounce bonus/penalty
    traits["variance"] = distinct / 4.0
    if distinct <= 1:
        traits["variance"] -= 0.05
    elif distinct >= 3:
        traits["variance"] += 0.05

    # Final clamp
    for k in list(traits.keys()):
        traits[k] = _clamp01(float(traits[k]))

    return traits
