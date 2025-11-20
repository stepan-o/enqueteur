from __future__ import annotations

import json
from pathlib import Path

from loopforge.reporting import DaySummary, AgentDayStats, EpisodeSummary, summarize_episode
from loopforge.psych.supervisor_weather import (
    build_supervisor_weather,
    SupervisorEpisodeWeather,
)
from loopforge.narrative.episode_recaps import build_episode_recap
from loopforge.analysis_api import episode_summary_to_dict


def _mk_day(idx: int, *, tension: float, sup: float, agents: dict[str, dict]) -> DaySummary:
    stats: dict[str, AgentDayStats] = {}
    for name, cfg in agents.items():
        stats[name] = AgentDayStats(
            name=name,
            role=cfg.get("role", "qa"),
            guardrail_count=int(cfg.get("g", 0)),
            context_count=int(cfg.get("c", 0)),
            avg_stress=float(cfg.get("stress", 0.0)),
        )
    return DaySummary(
        day_index=idx,
        perception_mode="accurate",
        tension_score=float(tension),
        agent_stats=stats,
        total_incidents=0,
        supervisor_activity=float(sup),
        beliefs={},
        belief_attributions={},
        reflection_states={},
        emotion_states={},
    )


def test_determinism_same_input_same_output():
    day0 = _mk_day(0, tension=0.10, sup=0.05, agents={
        "Delta": {"role": "optimizer", "g": 1, "c": 9, "stress": 0.1},
        "Nova": {"role": "qa", "g": 2, "c": 8, "stress": 0.2},
    })
    day1 = _mk_day(1, tension=0.20, sup=0.10, agents={
        "Delta": {"role": "optimizer", "g": 2, "c": 8, "stress": 0.2},
        "Nova": {"role": "qa", "g": 3, "c": 7, "stress": 0.2},
    })
    ep = EpisodeSummary(days=[day0, day1], agents={}, tension_trend=[0.10, 0.20])

    a = build_supervisor_weather(ep, [day0, day1])
    b = build_supervisor_weather(ep, [day0, day1])

    assert isinstance(a, SupervisorEpisodeWeather)
    assert a == b


def test_pressure_targeting_high_pressure_and_misalignment():
    # High tension + stress + low trust proxied by heavy guardrails
    day0 = _mk_day(0, tension=0.80, sup=0.30, agents={
        "Delta": {"role": "optimizer", "g": 9, "c": 1, "stress": 0.85},
        "Nova": {"role": "qa", "g": 1, "c": 9, "stress": 0.10},
    })
    ep = EpisodeSummary(days=[day0], agents={}, tension_trend=[0.80])

    sw = build_supervisor_weather(ep, [day0])
    d0 = sw.days[0]
    assert d0.global_pressure == "high"
    # Expect at least one firm or hard target under these conditions
    assert any(t.pressure_level in {"firm", "hard"} for t in d0.targets)
    assert 0.0 <= d0.alignment_score <= 1.0


def test_low_pressure_aligned():
    # Low tension + low stress + context-heavy should yield low pressure and no targets
    day0 = _mk_day(0, tension=0.05, sup=0.05, agents={
        "Delta": {"role": "optimizer", "g": 1, "c": 9, "stress": 0.05},
        "Nova": {"role": "qa", "g": 0, "c": 10, "stress": 0.05},
    })
    ep = EpisodeSummary(days=[day0], agents={}, tension_trend=[0.05])

    sw = build_supervisor_weather(ep, [day0])
    d0 = sw.days[0]
    assert d0.global_pressure == "low"
    assert d0.alignment_score >= 0.5
    assert all(t.pressure_level != "hard" for t in d0.targets)


def test_recap_integration_adds_supervisor_lines():
    day0 = _mk_day(0, tension=0.30, sup=0.10, agents={
        "Delta": {"role": "optimizer", "g": 5, "c": 5, "stress": 0.30},
    })
    # Let summarize_episode attach supervisor_weather via fail-soft builder
    ep = summarize_episode([day0])

    recap = build_episode_recap(ep, [day0], characters={})
    lines = getattr(recap, "pressure_lines", None) or []
    # Expect at least one line mentioning Supervisor mood baseline
    assert any("Supervisor mood this episode" in s for s in lines)


def test_export_shape_contains_supervisor_weather():
    day0 = _mk_day(0, tension=0.25, sup=0.05, agents={
        "Delta": {"role": "optimizer", "g": 4, "c": 6, "stress": 0.2},
    })
    ep = summarize_episode([day0])

    out = episode_summary_to_dict(ep)
    assert "supervisor_weather" in out
    sw = out["supervisor_weather"]
    assert isinstance(sw, dict)
    assert set(sw.keys()) == {"mood_baseline", "mood_trend", "days"}
    assert isinstance(sw["days"], list)
    if sw["days"]:
        d = sw["days"][0]
        # Nested structure keys
        for k in ("day_index", "mood", "tone_volatility", "global_pressure", "alignment_score", "targets"):
            assert k in d
        # Targets must be JSON-serializable dicts
        for t in d.get("targets", []):
            assert set(t.keys()) == {"agent_name", "pressure_level", "reason", "misalignment_score"}
