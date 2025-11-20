from __future__ import annotations

from typing import List, Dict

from loopforge.reporting import DaySummary, AgentDayStats, EpisodeSummary
from loopforge.schema.types import BeliefAttribution, BeliefState, EpisodeStoryArc
from loopforge.psych.trait_drift import derive_trait_snapshot


def _episode(
    *,
    stresses: List[float],
    causes: List[str],
    belief_trust_start: float | None = None,
    belief_trust_end: float | None = None,
    emotional_color: str | None = None,
    supervisor_pattern: str | None = None,
) -> EpisodeSummary:
    assert len(stresses) == len(causes)
    days: List[DaySummary] = []
    for idx, (s, cause) in enumerate(zip(stresses, causes)):
        ds = DaySummary(
            day_index=idx,
            perception_mode="accurate",
            tension_score=0.0,
            agent_stats={
                "Delta": AgentDayStats(name="Delta", role="optimizer", guardrail_count=10, context_count=0, avg_stress=s)
            },
            total_incidents=0,
            beliefs={},
            belief_attributions={},
            reflection_states={},
            emotion_states={},
        )
        ds.belief_attributions["Delta"] = BeliefAttribution(cause=cause, confidence=0.7, rationale="")
        days.append(ds)

    # Optional belief supervisor_trust start/end
    if belief_trust_start is not None:
        days[0].beliefs["Delta"] = BeliefState(
            supervisor_trust=belief_trust_start,
            guardrail_faith=0.5,
            self_efficacy=0.5,
            world_predictability=0.5,
            incident_attribution="world",
        )
    if belief_trust_end is not None:
        days[-1].beliefs["Delta"] = BeliefState(
            supervisor_trust=belief_trust_end,
            guardrail_faith=0.5,
            self_efficacy=0.5,
            world_predictability=0.5,
            incident_attribution="world",
        )

    agents = {
        "Delta": type("_AES", (), {
            "name": "Delta",
            "role": "optimizer",
            "guardrail_total": 10 * len(stresses),
            "context_total": 0,
            "trait_deltas": {},
            "stress_start": stresses[0],
            "stress_end": stresses[-1],
            "representative_reflection": None,
            "visual": "",
            "vibe": "",
            "tagline": "",
        })()
    }

    ep = EpisodeSummary(days=days, agents=agents, tension_trend=[0.0 for _ in stresses])
    if emotional_color is not None or supervisor_pattern is not None:
        ep.story_arc = EpisodeStoryArc(
            arc_type="uncertain",
            tension_pattern="unknown",
            supervisor_pattern=supervisor_pattern or "unknown",
            emotional_color=emotional_color or "unknown",
            summary_lines=["."],
        )
    return ep


def test_resilience_increases_when_stress_falls():
    ep = _episode(stresses=[0.30, 0.20], causes=["system", "system"])
    snap = derive_trait_snapshot(None, ep, agent_name="Delta")
    assert snap["resilience"] >= 0.5


def test_caution_increases_when_random_dominant():
    ep = _episode(stresses=[0.20, 0.20, 0.20], causes=["random", "random", "system"])
    snap = derive_trait_snapshot(None, ep, agent_name="Delta")
    assert snap["caution"] > 0.5


def test_agency_increases_with_self_dominant_and_decreases_with_supervisor():
    ep_self = _episode(stresses=[0.20, 0.18, 0.16], causes=["self", "self", "self"])
    snap_self = derive_trait_snapshot(None, ep_self, agent_name="Delta")
    assert snap_self["agency"] > 0.5

    ep_sup = _episode(stresses=[0.20, 0.22, 0.25], causes=["supervisor", "supervisor", "supervisor"])
    snap_sup = derive_trait_snapshot(None, ep_sup, agent_name="Delta")
    assert snap_sup["agency"] < 0.5


def test_emotional_exhaustion_reduces_resilience():
    ep = _episode(stresses=[0.30, 0.25], causes=["system", "system"], emotional_color="exhaustion")
    snap = derive_trait_snapshot(None, ep, agent_name="Delta")
    assert snap["resilience"] <= 0.5


def test_belief_drift_carries_into_trust_supervisor():
    ep = _episode(
        stresses=[0.20, 0.20],
        causes=["system", "system"],
        belief_trust_start=0.3,
        belief_trust_end=0.7,
    )
    snap = derive_trait_snapshot(None, ep, agent_name="Delta")
    # 0.5 + 0.5*(0.7-0.3) = 0.5 + 0.2 = 0.7 (before clamp and other tweaks)
    assert snap["trust_supervisor"] >= 0.7 - 1e-6


def test_variance_logic_counts_distinct_causes():
    ep_same = _episode(stresses=[0.2, 0.2, 0.2], causes=["system", "system", "system"])
    snap_same = derive_trait_snapshot(None, ep_same, agent_name="Delta")
    assert snap_same["variance"] <= 0.5

    ep_many = _episode(stresses=[0.2, 0.21, 0.22, 0.23], causes=["system", "random", "self", "supervisor"])
    snap_many = derive_trait_snapshot(None, ep_many, agent_name="Delta")
    assert snap_many["variance"] >= 0.5
