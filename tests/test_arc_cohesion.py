from __future__ import annotations

from loopforge.arc_cohesion import (
    compute_reflection_tone,
    compute_arc_cohesion,
    build_arc_cohesion_line,
)
from loopforge.reporting import EpisodeSummary, AgentEpisodeStats, DaySummary, AgentDayStats
from loopforge.types import EpisodeStoryArc


def _mk_day(idx: int, tension: float = 0.0) -> DaySummary:
    return DaySummary(
        day_index=idx,
        perception_mode="accurate",
        tension_score=tension,
        agent_stats={},
        total_incidents=0,
        supervisor_activity=0.0,
        beliefs={},
        belief_attributions={},
        reflection_states={},
        emotion_states={},
    )


def test_compute_reflection_tone():
    # All agents end low stress (<0.10) -> calming
    agents_a = {
        "Alpha": AgentEpisodeStats(
            name="Alpha", role="qa", guardrail_total=0, context_total=0,
            trait_deltas={}, stress_start=0.2, stress_end=0.05,
            representative_reflection=None, trait_snapshot=None,
        ),
        "Delta": AgentEpisodeStats(
            name="Delta", role="optimizer", guardrail_total=0, context_total=0,
            trait_deltas={}, stress_start=0.2, stress_end=0.09,
            representative_reflection=None, trait_snapshot=None,
        ),
    }
    ep_a = EpisodeSummary(days=[_mk_day(0), _mk_day(1)], agents=agents_a, tension_trend=[0.2, 0.1])
    assert compute_reflection_tone(ep_a) == "calming"

    # All agents end high stress (>0.30) -> tense
    agents_b = {
        "Alpha": AgentEpisodeStats(
            name="Alpha", role="qa", guardrail_total=0, context_total=0,
            trait_deltas={}, stress_start=0.1, stress_end=0.35,
            representative_reflection=None, trait_snapshot=None,
        ),
        "Delta": AgentEpisodeStats(
            name="Delta", role="optimizer", guardrail_total=0, context_total=0,
            trait_deltas={}, stress_start=0.15, stress_end=0.40,
            representative_reflection=None, trait_snapshot=None,
        ),
    }
    ep_b = EpisodeSummary(days=[_mk_day(0), _mk_day(1)], agents=agents_b, tension_trend=[0.1, 0.4])
    assert compute_reflection_tone(ep_b) == "tense"

    # Mixed -> mixed
    agents_c = {
        "Alpha": AgentEpisodeStats(
            name="Alpha", role="qa", guardrail_total=0, context_total=0,
            trait_deltas={}, stress_start=0.1, stress_end=0.05,
            representative_reflection=None, trait_snapshot=None,
        ),
        "Delta": AgentEpisodeStats(
            name="Delta", role="optimizer", guardrail_total=0, context_total=0,
            trait_deltas={}, stress_start=0.15, stress_end=0.40,
            representative_reflection=None, trait_snapshot=None,
        ),
    }
    ep_c = EpisodeSummary(days=[_mk_day(0), _mk_day(1)], agents=agents_c, tension_trend=[0.15, 0.2])
    assert compute_reflection_tone(ep_c) == "mixed"


def test_compute_arc_cohesion():
    # "unwinding" + "calming" -> cohesive episode arc
    assert compute_arc_cohesion("decompression", "calming") == "cohesive episode arc"
    # "unwinding" + "tense" -> fragmented arc
    assert compute_arc_cohesion("decompression", "tense") == "fragmented arc"
    # "building tension" + "calming" -> mild mismatch
    assert compute_arc_cohesion("escalation", "calming") == "mild mismatch"


def test_build_arc_cohesion_line():
    agents = {
        "Alpha": AgentEpisodeStats(
            name="Alpha", role="qa", guardrail_total=0, context_total=0,
            trait_deltas={}, stress_start=0.2, stress_end=0.05,
            representative_reflection=None, trait_snapshot=None,
        ),
        "Delta": AgentEpisodeStats(
            name="Delta", role="optimizer", guardrail_total=0, context_total=0,
            trait_deltas={}, stress_start=0.2, stress_end=0.07,
            representative_reflection=None, trait_snapshot=None,
        ),
    }
    ep = EpisodeSummary(days=[_mk_day(0), _mk_day(1)], agents=agents, tension_trend=[0.3, 0.15])
    arc = EpisodeStoryArc(
        arc_type="decompression",
        tension_pattern="steady_cooldown",
        supervisor_pattern="background",
        emotional_color="steady_calm",
        summary_lines=["Cooling off overall."],
    )
    line = build_arc_cohesion_line(ep, arc)
    # Ensure one of the expected verdict substrings is present
    assert any(s in line for s in ("cohesive episode arc", "mild mismatch", "fragmented arc"))
