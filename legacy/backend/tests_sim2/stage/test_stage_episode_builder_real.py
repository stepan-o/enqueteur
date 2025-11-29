from __future__ import annotations

from types import SimpleNamespace

from loopforge.analytics.reporting import DaySummary, EpisodeSummary, AgentDayStats, AgentEpisodeStats
from legacy.backend.loopforge_sim2 import build_stage_episode


def _make_day(day_index: int) -> DaySummary:
    agent_stats = {
        "Alpha": AgentDayStats(name="Alpha", role="scout", guardrail_count=1, context_count=2, avg_stress=0.3),
        "Beta": AgentDayStats(name="Beta", role="worker", guardrail_count=0, context_count=1, avg_stress=0.1),
    }
    return DaySummary(
        day_index=day_index,
        perception_mode="accurate",
        tension_score=0.2 + 0.1 * day_index,
        agent_stats=agent_stats,
        total_incidents=day_index,
        supervisor_activity=0.05 * day_index,
    )


def _make_episode(days: list[DaySummary]) -> EpisodeSummary:
    agents: dict[str, AgentEpisodeStats] = {}
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
        trait_snapshot={"risk_aversion": 0.5},
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
    return EpisodeSummary(days=days, agents=agents, tension_trend=[0.1, 0.3], episode_id="ep-9", run_id="run-9", episode_index=9)


def test_builder_real_mapping_with_narrative(monkeypatch):
    days = [_make_day(0), _make_day(1)]
    ep = _make_episode(days)

    # Monkeypatch narrative builders to return stable shapes
    def fake_build_day_narrative(day_summary, day_index, previous_day_summary=None):
        # emulate object with attributes used in builder
        return SimpleNamespace(
            agent_beats=[SimpleNamespace(name="Alpha", intro="Intro", perception_line="Perceive", actions_line="Act", closing_line="Close")],
            day_intro=f"Day {day_index} begins",
            supervisor_line="Supervisor watches",
            day_outro=f"Day {day_index} ends",
        )

    def fake_build_episode_recap(episode_summary, day_summaries, character_defs):
        return SimpleNamespace(
            intro="Episode recap intro",
            per_agent_blurbs={"Alpha": "Alpha did things", "Beta": "Beta worked"},
            closing="The end",
            story_arc_lines=["Arc A", "Arc B"],
            world_pulse_lines=["Pulse 1"],
            micro_incident_lines=["M1", "M2"],
            pressure_lines=["Pressure rising"],
            arc_cohesion="Cohesive",
            memory_line="Memories persist",
        )

    import legacy.backend.loopforge_sim2.stage.builder as builder_mod
    monkeypatch.setattr(builder_mod, "build_day_narrative", fake_build_day_narrative)
    monkeypatch.setattr(builder_mod, "build_episode_recap", fake_build_episode_recap)

    stage_ep = build_stage_episode(ep, ep.days, story_arc=None, long_memory=None, character_defs=None, include_narrative=True)

    # Episode-level checks
    assert stage_ep.episode_id == "ep-9"
    assert stage_ep.tension_trend == [0.1, 0.3]
    assert set(stage_ep.agents.keys()) == {"Alpha", "Beta"}
    assert any(nb.kind == "recap_intro" for nb in stage_ep.narrative)

    # Per-day checks
    assert len(stage_ep.days) == 2
    d1 = stage_ep.days[1]
    assert d1.total_incidents == 1
    assert d1.supervisor_activity == 0.05
    # Per-agent day narratives
    assert any(n.agent_name == "Alpha" and n.kind == "beat" for n in d1.agents["Alpha"].narrative)

    # Serialization must be JSON-safe
    as_dict = stage_ep.to_dict()
    # Simple structural assertions
    assert isinstance(as_dict["days"], list)
    assert isinstance(as_dict["agents"], dict)
