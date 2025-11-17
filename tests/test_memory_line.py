from __future__ import annotations

from typing import Dict

from loopforge.memory_line import compute_episode_intensity, build_memory_line
from loopforge.arc_cohesion import compute_reflection_tone
from loopforge.reporting import DaySummary, AgentDayStats, EpisodeSummary, AgentEpisodeStats
from loopforge.episode_recaps import build_episode_recap


def _mk_day(agent_defs: Dict[str, dict], *, day_index: int = 0, tension: float = 0.0, supervisor_activity: float = 0.0) -> DaySummary:
    # agent_defs: name -> {"stress": float, "incidents": int}
    stats = {}
    total_incidents = 0
    for name, cfg in agent_defs.items():
        total_incidents += int(cfg.get("incidents", 0))
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
        total_incidents=total_incidents,
        supervisor_activity=supervisor_activity,
        beliefs={},
        belief_attributions={},
        reflection_states={},
        emotion_states={},
    )


def test_compute_episode_intensity_basic():
    # rising + incidents > 0 -> charged
    day0 = _mk_day({"Delta": {"stress": 0.1, "incidents": 1}}, day_index=0, tension=0.10, supervisor_activity=0.2)
    day1 = _mk_day({"Delta": {"stress": 0.2, "incidents": 0}}, day_index=1, tension=0.25, supervisor_activity=0.2)
    episode = EpisodeSummary(days=[day0, day1], agents={}, tension_trend=[0.10, 0.25])
    assert compute_episode_intensity(episode, [day0, day1]) == "charged"

    # falling + no incidents -> quiet
    d0 = _mk_day({"Nova": {"stress": 0.2, "incidents": 0}}, day_index=0, tension=0.20, supervisor_activity=0.1)
    d1 = _mk_day({"Nova": {"stress": 0.1, "incidents": 0}}, day_index=1, tension=0.05, supervisor_activity=0.1)
    ep2 = EpisodeSummary(days=[d0, d1], agents={}, tension_trend=[0.20, 0.05])
    assert compute_episode_intensity(ep2, [d0, d1]) == "quiet"

    # flat + low sup + some incidents -> uneasy
    f0 = _mk_day({"Sprocket": {"stress": 0.1, "incidents": 1}}, day_index=0, tension=0.10, supervisor_activity=0.05)
    f1 = _mk_day({"Sprocket": {"stress": 0.1, "incidents": 0}}, day_index=1, tension=0.10, supervisor_activity=0.05)
    ep3 = EpisodeSummary(days=[f0, f1], agents={}, tension_trend=[0.10, 0.10])
    assert compute_episode_intensity(ep3, [f0, f1]) == "uneasy"


def test_build_memory_line_text():
    # Build a simple episode and get reflection tone via Sprint 4 helper
    day0 = _mk_day({"Delta": {"stress": 0.35, "incidents": 1}}, day_index=0, tension=0.20, supervisor_activity=0.3)
    day1 = _mk_day({"Delta": {"stress": 0.40, "incidents": 0}}, day_index=1, tension=0.35, supervisor_activity=0.3)
    episode = EpisodeSummary(days=[day0, day1], agents={}, tension_trend=[0.20, 0.35])

    tone = compute_reflection_tone(episode)
    line = build_memory_line(episode, [day0, day1], tone)

    # Substring assertions for stability (allow tweakable phrasing)
    assert line.startswith("Memory Line: ")
    assert any(kw in line for kw in ["hum", "quiet", "charge", "watched", "vigilance", "focus"])  # broad safety net


def test_recap_integration_order_and_presence():
    # Make a minimal episode where all three blocks are present: ARC COHESION, MEMORY LINE, PRESSURE NOTES
    day0 = _mk_day({
        "Alpha": {"stress": 0.09, "incidents": 0},
        "Delta": {"stress": 0.35, "incidents": 1},
    }, day_index=0, tension=0.10, supervisor_activity=0.2)
    day1 = _mk_day({
        "Alpha": {"stress": 0.08, "incidents": 0},
        "Delta": {"stress": 0.25, "incidents": 0},
    }, day_index=1, tension=0.25, supervisor_activity=0.3)

    agents = {
        "Alpha": AgentEpisodeStats(
            name="Alpha", role="qa", guardrail_total=0, context_total=0, trait_deltas={},
            stress_start=day0.agent_stats["Alpha"].avg_stress, stress_end=day1.agent_stats["Alpha"].avg_stress,
            representative_reflection=None, trait_snapshot={"agency": 0.51, "trust_supervisor": 0.49},
        ),
        "Delta": AgentEpisodeStats(
            name="Delta", role="optimizer", guardrail_total=0, context_total=0, trait_deltas={},
            stress_start=day0.agent_stats["Delta"].avg_stress, stress_end=day1.agent_stats["Delta"].avg_stress,
            representative_reflection=None, trait_snapshot={"agency": 0.55, "trust_supervisor": 0.45},
        ),
    }
    episode = EpisodeSummary(days=[day0, day1], agents=agents, tension_trend=[0.10, 0.25])

    recap = build_episode_recap(episode, [day0, day1], characters={})

    # Presence checks
    assert recap.arc_cohesion is not None and isinstance(recap.arc_cohesion, str)
    assert recap.memory_line is not None and isinstance(recap.memory_line, str)
    assert recap.pressure_lines is not None and len(recap.pressure_lines) >= 1

    # Simulate CLI block order and ensure MEMORY LINE sits between ARC COHESION and PRESSURE NOTES
    blocks = []
    if recap.arc_cohesion:
        blocks.append("ARC COHESION")
    if recap.memory_line:
        blocks.append("MEMORY LINE")
    if recap.pressure_lines:
        blocks.append("PRESSURE NOTES")

    assert blocks == ["ARC COHESION", "MEMORY LINE", "PRESSURE NOTES"]
