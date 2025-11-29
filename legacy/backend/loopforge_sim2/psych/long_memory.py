from __future__ import annotations
"""
Deterministic Episode Long Memory engine (Sprint 10, EA-IV)
- Pure, read-only mapping from per-episode aggregates + prior memory → AgentLongMemory
- No randomness, no LLM; lives above the seam; additive only
"""
from typing import Optional, Mapping, Sequence

from loopforge.schema.types import AgentLongMemory, EpisodeStoryArc


MAX_STEP_STRONG = 0.05
MAX_STEP_MEDIUM = 0.03
MAX_STEP_SMALL = 0.02


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def update_long_memory_for_agent(
    prev: Optional[AgentLongMemory],
    *,
    name: str,
    stress_start: float,
    stress_end: float,
    guardrail_total: int,
    context_total: int,
    blame_counts: Mapping[str, int],
    blame_timeline: Sequence[str],
    incidents_in_episode: int,
    story_arc: Optional[EpisodeStoryArc],
) -> AgentLongMemory:
    """Update or create long-horizon memory deterministically.

    Canonical blame normalization and small-step clamped drifts ensure stability
    and reproducibility across episodes.
    """
    # Baseline when no previous memory exists
    if prev is None:
        prev = AgentLongMemory(
            name=name,
            episodes=0,
            cumulative_stress=0.0,
            cumulative_incidents=0,
            trust_supervisor=0.5,
            self_trust=0.5,
            stability=0.5,
            reactivity=0.5,
            agency=0.5,
        )

    # Episode aggregates
    episodes = int(prev.episodes) + 1
    try:
        s0 = float(stress_start or 0.0)
        s1 = float(stress_end or 0.0)
    except Exception:
        s0 = 0.0
        s1 = 0.0
    episode_mean_stress = max(0.0, (s0 + s1) / 2.0)
    cumulative_stress = float(prev.cumulative_stress or 0.0) + episode_mean_stress
    cumulative_incidents = int(max(0, int(prev.cumulative_incidents or 0)) + max(0, int(incidents_in_episode or 0)))

    # Canonical blame normalization
    CANON = {"supervisor", "self", "system", "random"}
    sup_c = int(blame_counts.get("supervisor", 0) or 0)
    self_c = int(blame_counts.get("self", 0) or 0)
    sys_c = int(blame_counts.get("system", 0) or 0)
    rnd_c = int(blame_counts.get("random", 0) or 0)
    total_canon = max(1, sup_c + self_c + sys_c + rnd_c)
    frac_supervisor = sup_c / total_canon
    frac_self = self_c / total_canon
    frac_system = sys_c / total_canon
    frac_random = rnd_c / total_canon

    # Diversity for stability/reactivity: count distinct canonical causes seen
    try:
        distinct = len({c for c in blame_timeline if isinstance(c, str) and c in CANON})
    except Exception:
        distinct = 0
    diversity = min(1.0, distinct / 4.0)

    # Identity drift rules (apply deltas then clamp)
    trust_supervisor = _clamp01(float(prev.trust_supervisor) + (MAX_STEP_MEDIUM * (frac_self + frac_system - frac_supervisor)))

    self_trust = _clamp01(float(prev.self_trust) + (MAX_STEP_MEDIUM * (frac_self - frac_random)))

    stress_delta = s1 - s0
    if stress_delta <= 0 and diversity <= 0.5:
        delta_stability = MAX_STEP_SMALL
    elif stress_delta > 0 or diversity > 0.75:
        delta_stability = -MAX_STEP_SMALL
    else:
        delta_stability = 0.0
    stability = _clamp01(float(prev.stability) + delta_stability)

    reactivity_signal = diversity - 0.5
    reactivity = _clamp01(float(prev.reactivity) + (MAX_STEP_SMALL * reactivity_signal))

    total = max(1, int(guardrail_total or 0) + int(context_total or 0))
    frac_guard = int(guardrail_total or 0) / total
    frac_context = int(context_total or 0) / total
    agency_signal = (frac_context - frac_guard) - (frac_supervisor * 0.25)
    agency = _clamp01(float(prev.agency) + (MAX_STEP_SMALL * agency_signal))

    # Optional tiny bias from story arc (kept sub-0.01)
    if story_arc is not None:
        try:
            if getattr(story_arc, "arc_type", None) == "decompression":
                stability = _clamp01(stability + 0.01)
        except Exception:
            pass

    return AgentLongMemory(
        name=name,
        episodes=episodes,
        cumulative_stress=cumulative_stress,
        cumulative_incidents=cumulative_incidents,
        trust_supervisor=trust_supervisor,
        self_trust=self_trust,
        stability=stability,
        reactivity=reactivity,
        agency=agency,
    )
