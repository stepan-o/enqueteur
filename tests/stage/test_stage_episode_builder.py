from __future__ import annotations

import json
from typing import Dict

from loopforge.analytics.reporting import DaySummary, EpisodeSummary, AgentDayStats, AgentEpisodeStats
from loopforge.stage import (
    StageEpisode,
    StageDay,
    StageAgentDayView,
    StageAgentSummary,
    StageNarrativeBlock,
    build_stage_episode,
)


def _make_day(day_index: int) -> DaySummary:
    agent_stats = {
        "Alpha": AgentDayStats(name="Alpha", role="scout", guardrail_count=1, context_count=2, avg_stress=0.3),
        "Beta": AgentDayStats(name="Beta", role="worker", guardrail_count=0, context_count=1, avg_stress=0.1),
    }
    return DaySummary(
        day_index=day_index,
        perception_mode="accurate",
        tension_score=0.2,
        agent_stats=agent_stats,
        total_incidents=0,
        supervisor_activity=0.0,
    )


def _make_episode(days: list[DaySummary]) -> EpisodeSummary:
    agents: Dict[str, AgentEpisodeStats] = {}
    agents["Alpha"] = AgentEpisodeStats(
        name="Alpha",
        role="scout",
        guardrail_total=2,
        context_total=3,
        trait_deltas={},
        stress_start=0.2,
        stress_end=0.4,
        representative_reflection=None,
        visual="",
        vibe="",
        tagline="",
        trait_snapshot=None,
    )
    agents["Beta"] = AgentEpisodeStats(
        name="Beta",
        role="worker",
        guardrail_total=0,
        context_total=2,
        trait_deltas={},
        stress_start=0.1,
        stress_end=0.2,
        representative_reflection=None,
        visual="",
        vibe="",
        tagline="",
        trait_snapshot=None,
    )
    return EpisodeSummary(days=days, agents=agents, tension_trend=[0.1, 0.2], episode_id="ep-1", run_id="run-1", episode_index=1)


def test_stage_episode_instantiation_and_serialization():
    day0 = _make_day(0)
    day1 = _make_day(1)
    ep = _make_episode([day0, day1])

    stage_ep = build_stage_episode(ep, ep.days, story_arc=None, long_memory=None, character_defs=None)

    # Structure checks
    assert isinstance(stage_ep, StageEpisode)
    assert stage_ep.episode_id == "ep-1"
    assert stage_ep.run_id == "run-1"
    assert stage_ep.episode_index == 1
    assert len(stage_ep.days) == 2
    assert set(stage_ep.agents.keys()) == {"Alpha", "Beta"}

    # Day structure
    d0 = stage_ep.days[0]
    assert isinstance(d0, StageDay)
    assert d0.day_index == 0
    assert d0.perception_mode == "accurate"
    assert d0.tension_score == 0.2
    assert set(d0.agents.keys()) == {"Alpha", "Beta"}
    assert isinstance(d0.agents["Alpha"], StageAgentDayView)

    # Agent summary structure
    a_alpha = stage_ep.agents["Alpha"]
    assert isinstance(a_alpha, StageAgentSummary)
    assert a_alpha.guardrail_total == 2
    assert a_alpha.context_total == 3

    # Dict serialization for all primary dataclasses
    as_dict = stage_ep.to_dict()
    json_str = json.dumps(as_dict)  # must be JSON-serializable
    assert isinstance(json_str, str)


def test_narrative_blocks_are_present_but_empty():
    ep = _make_episode([_make_day(0)])
    stage_ep = build_stage_episode(ep, ep.days, story_arc=None, long_memory=None, character_defs=None)
    # Placeholders should be empty lists (not None)
    assert stage_ep.narrative == []
    assert all(d.narrative == [] for d in stage_ep.days)
