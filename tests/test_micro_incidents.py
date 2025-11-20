from __future__ import annotations

import json
from dataclasses import asdict
from typing import Dict

from loopforge.analytics.reporting import DaySummary, AgentDayStats, EpisodeSummary, summarize_episode
from loopforge.narrative.episode_recaps import build_episode_recap
from loopforge.psych.micro_incidents import build_micro_incidents, MicroIncident


def _mk_day(idx: int, *, tension: float = 0.0, agents: Dict[str, Dict] | None = None) -> DaySummary:
    stats: Dict[str, AgentDayStats] = {}
    agents = agents or {}
    for name, cfg in agents.items():
        stats[name] = AgentDayStats(
            name=name,
            role=cfg.get("role", "qa"),
            guardrail_count=cfg.get("g", 0),
            context_count=cfg.get("c", 0),
            avg_stress=cfg.get("stress", 0.0),
            incidents_nearby=cfg.get("inc", 0),
        )
    return DaySummary(
        day_index=idx,
        perception_mode="accurate",
        tension_score=tension,
        agent_stats=stats,
        total_incidents=sum(int(getattr(s, "incidents_nearby", 0) or 0) for s in stats.values()),
        supervisor_activity=0.0,
        beliefs={},
        belief_attributions={},
        reflection_states={},
        emotion_states={},
    )


def test_determinism_same_episode_twice_identical():
    days = [
        _mk_day(0, tension=0.10, agents={"Delta": {"stress": 0.15}, "Nova": {"stress": 0.05}}),
        _mk_day(1, tension=0.20, agents={"Delta": {"stress": 0.20}, "Nova": {"stress": 0.10}}),
    ]
    ep = summarize_episode(days, episode_id="ep-det-123", run_id="run-x", episode_index=0)

    a = build_micro_incidents(ep)
    b = build_micro_incidents(ep)

    # Compare as JSON-serializable dicts for stability
    def _to_dict(mi: MicroIncident) -> dict:
        return {
            "day_index": mi.day_index,
            "incident_type": mi.incident_type,
            "severity": mi.severity,
            "agents_involved": list(mi.agents_involved),
            "summary": mi.summary,
        }

    assert [_to_dict(x) for x in a] == [_to_dict(x) for x in b]


def test_signal_sensitive_behavior_low_vs_high_tension():
    # Case A: low tension, low stress -> expect only low severity, skew to glitch/weirdness
    low = summarize_episode([
        _mk_day(0, tension=0.05, agents={"Delta": {"stress": 0.05}, "Nova": {"stress": 0.05}}),
    ], episode_id="ep-low", run_id="r", episode_index=0)
    low_inc = build_micro_incidents(low)
    for mi in low_inc:
        assert mi.severity == "low"
        assert mi.incident_type in {"glitch", "weirdness", "friction", "tension_spike"}

    # Case B: high tension or rising trend -> expect at least one non-low or pressured type
    high = summarize_episode([
        _mk_day(0, tension=0.60, agents={"Delta": {"stress": 0.40}, "Nova": {"stress": 0.35}}),
        _mk_day(1, tension=0.80, agents={"Delta": {"stress": 0.50}, "Nova": {"stress": 0.45}}),
    ], episode_id="ep-high", run_id="r", episode_index=0)
    hi_inc = build_micro_incidents(high)
    assert any(mi.incident_type in {"tension_spike", "friction"} for mi in hi_inc)
    assert any(mi.severity in {"medium", "high"} for mi in hi_inc)


essential_blocks = ("Day ",)


def test_recap_integration_exposes_micro_incident_lines():
    days = [
        _mk_day(0, tension=0.10, agents={"Delta": {"stress": 0.15}, "Nova": {"stress": 0.05}}),
        _mk_day(1, tension=0.30, agents={"Delta": {"stress": 0.25}, "Nova": {"stress": 0.20}}),
    ]
    ep = summarize_episode(days, episode_id="ep-recap", run_id="r", episode_index=0)

    recap = build_episode_recap(ep, ep.days, characters={})
    lines = getattr(recap, "micro_incident_lines", None)
    assert lines is not None and isinstance(lines, list)
    assert any(line.startswith("Day ") for line in lines)
    # Should mention at least one agent name deterministically present
    assert any("Delta" in line or "Nova" in line for line in lines)


def test_missing_world_pulse_does_not_crash():
    days = [
        _mk_day(0, tension=0.10, agents={"Delta": {"stress": 0.10}}),
        _mk_day(1, tension=0.20, agents={"Delta": {"stress": 0.20}}),
    ]
    ep = EpisodeSummary(days=days, agents={}, tension_trend=[0.10, 0.20], episode_id="ep-nopulse")
    # No world_pulse_history set
    inc = build_micro_incidents(ep)
    assert isinstance(inc, list)
