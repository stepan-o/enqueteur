from __future__ import annotations

from loopforge.analytics.reporting import EpisodeSummary, DaySummary, AgentEpisodeStats
from loopforge.narrative.episode_recaps import build_episode_recap
from loopforge.analytics.reporting import AgentDayStats
from loopforge.schema.types import BeliefAttribution


def _mk_day(idx: int, tension: float, name: str, role: str) -> DaySummary:
    stats = {name: AgentDayStats(name=name, role=role, guardrail_count=1, context_count=0, avg_stress=0.1)}
    ds = DaySummary(day_index=idx, perception_mode="accurate", tension_score=tension, agent_stats=stats, total_incidents=0)
    return ds


def _agent(name: str, role: str, g: int, c: int, s0: float | None, s1: float | None) -> AgentEpisodeStats:
    return AgentEpisodeStats(
        name=name,
        role=role,
        guardrail_total=g,
        context_total=c,
        trait_deltas={},
        stress_start=s0,
        stress_end=s1,
        representative_reflection=None,
        visual="",
        vibe="",
        tagline="",
    )


essentials = {"Delta": _agent("Delta", "optimizer", g=2, c=1, s0=0.2, s1=0.2)}


def test_episode_recap_includes_attribution_arc():
    # Build two days with attribution causes system -> self
    d0 = _mk_day(0, tension=0.2, name="Delta", role="optimizer")
    d1 = _mk_day(1, tension=0.25, name="Delta", role="optimizer")

    d0.belief_attributions = {"Delta": BeliefAttribution(cause="system", confidence=0.6, rationale="test")}
    d1.belief_attributions = {"Delta": BeliefAttribution(cause="self", confidence=0.6, rationale="test")}

    ep = EpisodeSummary(days=[d0, d1], agents=essentials, tension_trend=[0.2, 0.25])

    recap = build_episode_recap(ep, [d0, d1], characters={})

    text = " ".join(recap.per_agent_blurbs.values())
    assert "Attribution pattern: mostly system → self." in text
