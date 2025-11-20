from __future__ import annotations

from typing import Dict, List

from loopforge.narrative.pressure_notes import (
    classify_pressure,
    summarize_traits,
    build_pressure_lines,
)
from loopforge.reporting import DaySummary, AgentDayStats, EpisodeSummary, AgentEpisodeStats


def _mk_day(agent_defs: Dict[str, dict], *, day_index: int = 0, tension: float = 0.0, supervisor_activity: float = 0.0) -> DaySummary:
    # agent_defs: name -> {"stress": float, "incidents": int}
    stats = {}
    for name, cfg in agent_defs.items():
        stats[name] = AgentDayStats(
            name=name,
            role=cfg.get("role", "qa"),
            avg_stress=cfg.get("stress", 0.0),
            guardrail_count=cfg.get("g", 0),
            context_count=cfg.get("c", 0),
            incidents_nearby=cfg.get("incidents", 0),
        )
    return DaySummary(
        day_index=day_index,
        perception_mode="accurate",
        tension_score=tension,
        agent_stats=stats,
        total_incidents=sum(cfg.get("incidents", 0) for cfg in agent_defs.values()),
        supervisor_activity=supervisor_activity,
        beliefs={},
        belief_attributions={},
        reflection_states={},
        emotion_states={},
    )


def test_classify_pressure_basic():
    # Case 1: Rising tension + incidents > 0 → contains 'incidents' and 'rising tension'
    day0 = _mk_day({"Delta": {"stress": 0.1, "incidents": 1}}, day_index=0, tension=0.10, supervisor_activity=0.3)
    day1 = _mk_day({"Delta": {"stress": 0.2, "incidents": 0}}, day_index=1, tension=0.25, supervisor_activity=0.4)
    episode = EpisodeSummary(days=[day0, day1], agents={}, tension_trend=[0.10, 0.25])
    phrase = classify_pressure(episode, [day0, day1], "Delta")
    assert "incidents" in phrase and "rising tension" in phrase

    # Case 2: Rising tension + no incidents + low supervisor → 'rising tension' and 'silent supervisor'/'hands-off'
    day0b = _mk_day({"Nova": {"stress": 0.05, "incidents": 0}}, day_index=0, tension=0.10, supervisor_activity=0.05)
    day1b = _mk_day({"Nova": {"stress": 0.06, "incidents": 0}}, day_index=1, tension=0.20, supervisor_activity=0.05)
    episode_b = EpisodeSummary(days=[day0b, day1b], agents={}, tension_trend=[0.10, 0.20])
    phrase_b = classify_pressure(episode_b, [day0b, day1b], "Nova")
    assert "rising tension" in phrase_b and ("silent supervisor" in phrase_b or "hands-off" in phrase_b)

    # Case 3: Flat/low tension + no incidents + low supervisor → 'quiet shift' / 'hands-off supervision'
    day0c = _mk_day({"Sprocket": {"stress": 0.05, "incidents": 0}}, day_index=0, tension=0.05, supervisor_activity=0.0)
    day1c = _mk_day({"Sprocket": {"stress": 0.05, "incidents": 0}}, day_index=1, tension=0.05, supervisor_activity=0.0)
    episode_c = EpisodeSummary(days=[day0c, day1c], agents={}, tension_trend=[0.05, 0.05])
    phrase_c = classify_pressure(episode_c, [day0c, day1c], "Sprocket")
    assert ("quiet shift" in phrase_c) or ("hands-off supervision" in phrase_c)


def test_summarize_traits_highlights():
    # Highlights for agency↑ and trust_supervisor↓; others near neutral
    snapshot = {
        "agency": 0.55,
        "trust_supervisor": 0.45,
        "resilience": 0.51,
        "caution": 0.49,
        "variance": 0.50,
    }
    out = summarize_traits(snapshot)
    assert "agency↑" in out
    assert "trust_supervisor↓" in out

    # All neutral → traits stable
    neutral = {k: 0.5 for k in snapshot.keys()}
    out2 = summarize_traits(neutral)
    assert out2 == "traits stable"


def test_build_pressure_lines_layout():
    # Build episode with trait snapshots and simple patterns
    day0 = _mk_day(
        {
            "Alpha": {"stress": 0.12, "incidents": 0},
            "Delta": {"stress": 0.35, "incidents": 1},
            "Nova": {"stress": 0.07, "incidents": 0},
        },
        day_index=0,
        tension=0.10,
        supervisor_activity=0.1,
    )
    day1 = _mk_day(
        {
            "Alpha": {"stress": 0.08, "incidents": 0},
            "Delta": {"stress": 0.25, "incidents": 0},
            "Nova": {"stress": 0.15, "incidents": 0},
        },
        day_index=1,
        tension=0.20,
        supervisor_activity=0.1,
    )

    agents = {
        "Alpha": AgentEpisodeStats(
            name="Alpha",
            role="qa",
            guardrail_total=0,
            context_total=0,
            trait_deltas={},
            stress_start=day0.agent_stats["Alpha"].avg_stress,
            stress_end=day1.agent_stats["Alpha"].avg_stress,
            representative_reflection=None,
            trait_snapshot={"agency": 0.51, "trust_supervisor": 0.49},
        ),
        "Delta": AgentEpisodeStats(
            name="Delta",
            role="optimizer",
            guardrail_total=0,
            context_total=0,
            trait_deltas={},
            stress_start=day0.agent_stats["Delta"].avg_stress,
            stress_end=day1.agent_stats["Delta"].avg_stress,
            representative_reflection=None,
            trait_snapshot={"agency": 0.55, "trust_supervisor": 0.45},
        ),
        "Nova": AgentEpisodeStats(
            name="Nova",
            role="maintenance",
            guardrail_total=0,
            context_total=0,
            trait_deltas={},
            stress_start=day0.agent_stats["Nova"].avg_stress,
            stress_end=day1.agent_stats["Nova"].avg_stress,
            representative_reflection=None,
            trait_snapshot={"agency": 0.50, "trust_supervisor": 0.50},
        ),
    }

    episode = EpisodeSummary(days=[day0, day1], agents=agents, tension_trend=[0.10, 0.20])

    lines: List[str] = build_pressure_lines(episode, [day0, day1])

    # One line per agent with traits
    assert len(lines) == 3

    # Deterministic ordering: alphabetical
    assert lines[0].startswith("• Alpha:")
    assert lines[1].startswith("• Delta:")
    assert lines[2].startswith("• Nova:")

    # Ensure presence of "; traits stable." at least for Nova
    assert any(line.endswith("; traits stable.") for line in lines)
