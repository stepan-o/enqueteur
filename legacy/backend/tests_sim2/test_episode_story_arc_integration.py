from __future__ import annotations

import json
from pathlib import Path

from loopforge.analytics.reporting import EpisodeSummary, DaySummary, AgentEpisodeStats
from loopforge.narrative.episode_recaps import build_episode_recap
from loopforge.analytics.analysis_api import episode_summary_to_dict


def _mk_day(idx: int, tension: float) -> DaySummary:
    from loopforge.analytics.reporting import AgentDayStats
    return DaySummary(day_index=idx, perception_mode="accurate", tension_score=tension, agent_stats={}, total_incidents=0)


def _mk_ep(ten: list[float], agents: dict[str, AgentEpisodeStats]) -> EpisodeSummary:
    days = [_mk_day(i, t) for i, t in enumerate(ten)]
    ep = EpisodeSummary(days=days, agents=agents, tension_trend=ten)
    # Simulate story arc attachment as summarize_episode would do
    try:
        from loopforge.narrative.story_arc import derive_episode_story_arc
        ep.story_arc = derive_episode_story_arc(ep)
    except Exception:
        ep.story_arc = None
    return ep


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


def test_story_arc_recapped_and_exported(tmp_path: Path):
    agents = {
        "Delta": _agent("Delta", "optimizer", g=3, c=1, s0=0.30, s1=0.10),
    }
    ep = _mk_ep([0.30, 0.15, 0.10], agents)

    recap = build_episode_recap(ep, ep.days, characters={})
    # STORY ARC block expected when story_arc is present
    assert recap.story_arc_lines is not None
    assert any("Tension" in s or "Supervisor" in s or "Emotional" in s for s in recap.story_arc_lines)

    # Export dict contains story_arc key and JSON-serializes
    export = episode_summary_to_dict(ep)
    assert "story_arc" in export
    s = json.dumps(export)
    assert isinstance(s, str)
    # When present, arc_type must be one of known literals
    if export["story_arc"] is not None:
        assert export["story_arc"]["arc_type"] in {"decompression", "escalation", "back_and_forth", "flatline", "uncertain"}
