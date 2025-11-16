from __future__ import annotations

from loopforge.reporting import summarize_day, DaySummary, AgentDayStats
from loopforge.types import ActionLogEntry


def _mk_entry(step: int, name: str, role: str, mode: str, *, stress: float = 0.0):
    return ActionLogEntry(
        step=step,
        agent_name=name,
        role=role,
        mode=mode,
        intent="",
        move_to=None,
        targets=[],
        riskiness=0.0,
        narrative="",
        raw_action={},
        perception={
            "emotions": {"stress": stress, "curiosity": 0.5, "satisfaction": 0.5},
            "perception_mode": "accurate",
        },
        outcome=None,
    )


def test_reflection_states_populated_and_trend_day0_unknown_day1_classified():
    # Day 0: build entries for one agent
    entries_day0 = [
        _mk_entry(0, "Delta", "optimizer", "guardrail", stress=0.20),
        _mk_entry(1, "Delta", "optimizer", "guardrail", stress=0.20),
        _mk_entry(2, "Delta", "optimizer", "context", stress=0.21),
    ]
    ds0: DaySummary = summarize_day(day_index=0, entries=entries_day0, reflections_by_agent=None)

    assert hasattr(ds0, "reflection_states")
    assert isinstance(ds0.reflection_states, dict)
    assert "Delta" in ds0.reflection_states
    assert ds0.reflection_states["Delta"].stress_trend == "unknown"  # Day 0 must be unknown

    # Day 1: slightly lower stress to force 'falling'
    prev_stats = ds0.agent_stats
    entries_day1 = [
        _mk_entry(10, "Delta", "optimizer", "guardrail", stress=0.18),
        _mk_entry(11, "Delta", "optimizer", "guardrail", stress=0.18),
        _mk_entry(12, "Delta", "optimizer", "context", stress=0.18),
    ]
    ds1: DaySummary = summarize_day(
        day_index=1,
        entries=entries_day1,
        reflections_by_agent=None,
        previous_day_stats=prev_stats,
    )

    assert hasattr(ds1, "reflection_states") and "Delta" in ds1.reflection_states
    assert ds1.reflection_states["Delta"].stress_trend in {"rising", "falling", "flat"}
    assert ds1.reflection_states["Delta"].stress_trend == "falling"

    # rulebook_reliance bounds
    rel = ds1.reflection_states["Delta"].rulebook_reliance
    assert 0.0 <= rel <= 1.0
