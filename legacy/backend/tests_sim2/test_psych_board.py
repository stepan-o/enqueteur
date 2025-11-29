from __future__ import annotations

from legacy.backend.loopforge_sim2 import (
    stress_band,
    attr_cause_to_letter,
    mood_to_bucket,
    cell_code,
    build_psych_board,
)
from loopforge.analytics.reporting import DaySummary
from loopforge.analytics.reporting import AgentDayStats, EpisodeSummary
from loopforge.schema.types import BeliefAttribution, AgentEmotionState


def _mk_stats(name: str, role: str = "qa", stress: float = 0.0, g: int = 0, c: int = 0) -> AgentDayStats:
    return AgentDayStats(name=name, role=role, avg_stress=stress, guardrail_count=g, context_count=c)


def _mk_day(agent_defs):
    # agent_defs: dict[name] -> (stress, cause, mood)
    stats = {}
    attrs = {}
    emos = {}
    for name, (stress, cause, mood) in agent_defs.items():
        stats[name] = _mk_stats(name, stress=stress)
        if cause is not None:
            attrs[name] = BeliefAttribution(cause=cause, confidence=0.7 if cause != "random" else 0.2, rationale="")
        if mood is not None:
            # certainty/energy not needed for bucket mapping; set valid defaults
            emos[name] = AgentEmotionState(mood=mood, certainty="confident", energy="steady")
    return DaySummary(
        day_index=0,
        perception_mode="accurate",
        tension_score=0.0,
        agent_stats=stats,
        total_incidents=0,
        beliefs={},
        belief_attributions=attrs,
        reflection_states={},
        emotion_states=emos,
    )


def test_mappings_basic():
    # Stress band via reused daily logs thresholds
    assert stress_band(0.05) == "low"
    assert stress_band(0.10) == "mid"
    assert stress_band(0.35) == "high"

    # Attribution letter mapping
    assert attr_cause_to_letter("random") == "R"
    assert attr_cause_to_letter("system") == "S"
    assert attr_cause_to_letter("supervisor") == "U"
    assert attr_cause_to_letter("self") == "F"
    assert attr_cause_to_letter(None) == "-"
    assert attr_cause_to_letter("unknown") == "-"

    # Mood bucket mapping
    assert mood_to_bucket("calm") == "✓"
    assert mood_to_bucket("uneasy") == "?"
    assert mood_to_bucket("tense") == "!"
    assert mood_to_bucket("brittle") == "!"
    assert mood_to_bucket("mystery") == "."
    assert mood_to_bucket(None) == "."


def test_cell_code_and_board_layout():
    # Build three days with three agents
    day0 = _mk_day({
        "Alpha": (0.09, "random", "uneasy"),   # mid/R/?
        "Delta": (0.40, "supervisor", "tense"), # high/U/!
        "Nova": (0.05, "random", "calm"),      # low/R/✓
    })
    # second day
    day1 = _mk_day({
        "Alpha": (0.07, "system", "calm"),      # low/S/✓
        "Delta": (0.20, "self", "calm"),        # mid/F/✓ -> bucket ✓
        "Nova": (0.15, "system", "uneasy"),     # mid/S/?
    })
    # third day
    day2 = _mk_day({
        "Alpha": (0.06, "system", "tense"),     # low/S/! (tense -> !) even if low stress
        "Delta": (0.25, "random", "uneasy"),    # mid/R/?
        "Nova": (0.45, "supervisor", "brittle"),# high/U/!
    })

    episode = EpisodeSummary(days=[day0, day1, day2], agents={}, tension_trend=[])

    # Cell codes spot checks
    assert cell_code(day0, "Alpha") == "mid/R/?"
    assert cell_code(day0, "Delta") == "high/U/!"
    assert cell_code(day0, "Nova") == "low/R/✓"

    # Build board
    lines = build_psych_board(episode)

    # Header
    assert any(line.startswith("PSYCHOLOGY BOARD") for line in lines)
    days_line = next((l for l in lines if l.startswith("Days:")), None)
    assert days_line is not None and "0" in days_line and "1" in days_line and "2" in days_line

    # Rows in deterministic order: Alpha, Delta, Nova
    rows = [l for l in lines if l and not l.startswith("PSYCHOLOGY BOARD") and not l.startswith("=") and not l.startswith("Days:") and not set(l) <= set("- ")]
    # Extract just the three rows (after the dashed rule)
    # Find index of dashed line and slice after it
    rule_idx = next(i for i, l in enumerate(lines) if set(l) == {"-"})
    rows = lines[rule_idx + 1:]

    assert rows[0].startswith("Alpha")
    assert rows[1].startswith("Delta")
    assert rows[2].startswith("Nova")

    # Check codes presence in each row
    assert "mid/R/?" in rows[0] and "low/S/✓" in rows[0] and "low/S/!" in rows[0]
    assert "high/U/!" in rows[1] and "mid/F/✓" in rows[1] and "mid/R/?" in rows[1]
    assert "low/R/✓" in rows[2] and "mid/S/?" in rows[2] and "high/U/!" in rows[2]
