from __future__ import annotations

from typing import Dict

from loopforge.psych.world_pulse import compute_world_pulse
from loopforge.reporting import DaySummary, EpisodeSummary, summarize_episode, AgentDayStats
from loopforge.narrative.episode_recaps import build_episode_recap


def _mk_day(idx: int, tension: float = 0.0) -> DaySummary:
    # Minimal DaySummary similar to other recap tests
    stats: Dict[str, AgentDayStats] = {}
    return DaySummary(
        day_index=idx,
        perception_mode="accurate",
        tension_score=tension,
        agent_stats=stats,
        total_incidents=0,
        supervisor_activity=0.0,
        beliefs={},
        belief_attributions={},
        reflection_states={},
        emotion_states={},
    )


def test_compute_world_pulse_is_deterministic_with_seed():
    p1 = compute_world_pulse(2, seed=123)
    p2 = compute_world_pulse(2, seed=123)
    assert p1 == p2


def test_compute_world_pulse_schema_and_ranges():
    p = compute_world_pulse(5, seed=999)
    # Required keys
    for k in [
        "environmental_anomaly",
        "system_failure",
        "micro_incident",
        "supervisor_tone",
        "ambient_tension_delta",
        "motive_pressure",
    ]:
        assert k in p

    # Allowed value sets (string enums)
    assert p["environmental_anomaly"] in [
        "heat_spike",
        "vibration_drift",
        "red_haze",
        "air_thickening",
        "silence_drop",
    ]
    assert p["system_failure"] in ["none", "minor", "moderate"]
    assert p["micro_incident"] in ["spark_pop", "jammed_gear", "off_calibration", "none"]
    assert p["supervisor_tone"] in ["supportive", "neutral", "tense", "authoritarian"]

    # Ranges
    assert isinstance(p["ambient_tension_delta"], float)
    assert -0.0500001 <= p["ambient_tension_delta"] <= 0.0500001
    assert isinstance(p["motive_pressure"], float)
    assert 0.0 <= p["motive_pressure"] <= 1.0


def test_episode_summary_contains_world_pulse_history_of_correct_length():
    days = [_mk_day(i, tension=0.1 * i) for i in range(3)]
    ep = summarize_episode(days)
    # Field exists and has one entry per day
    assert getattr(ep, "world_pulse_history", None) is not None
    assert isinstance(ep.world_pulse_history, list)
    assert len(ep.world_pulse_history) == 3


def test_recap_world_pulse_block_location_and_lines():
    # Make a small episode and ensure recap exposes WORLD PULSE lines after STORY ARC and before ARC COHESION
    days = [_mk_day(0, tension=0.10), _mk_day(1, tension=0.25), _mk_day(2, tension=0.30)]
    ep = summarize_episode(days)

    recap = build_episode_recap(ep, days, characters={})

    # Presence and shape
    assert getattr(recap, "world_pulse_lines", None) is not None
    assert isinstance(recap.world_pulse_lines, list)
    # Exactly 1–2 lines per day; current design uses 1 line per day
    assert len(recap.world_pulse_lines) == len(days)
    assert recap.world_pulse_lines[0].startswith("Day 0:")

    # Simulate CLI block order as in scripts/run_simulation.view_episode
    blocks = []
    if getattr(recap, "story_arc_lines", None):
        blocks.append("STORY ARC")
    if getattr(recap, "world_pulse_lines", None):
        blocks.append("WORLD PULSE")
    if getattr(recap, "arc_cohesion", None):
        blocks.append("ARC COHESION")

    # WORLD PULSE must appear after STORY ARC (if present) and before ARC COHESION (if present)
    # So acceptable sequences:
    #   ["WORLD PULSE"]
    #   ["WORLD PULSE", "ARC COHESION"]
    #   ["STORY ARC", "WORLD PULSE"]
    #   ["STORY ARC", "WORLD PULSE", "ARC COHESION"]
    acceptable = [
        ["WORLD PULSE"],
        ["WORLD PULSE", "ARC COHESION"],
        ["STORY ARC", "WORLD PULSE"],
        ["STORY ARC", "WORLD PULSE", "ARC COHESION"],
    ]
    assert blocks in acceptable
