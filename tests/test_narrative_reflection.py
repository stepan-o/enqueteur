from __future__ import annotations

from loopforge.narrative.narrative_reflection import derive_reflection_state
from loopforge.analytics.reporting import AgentDayStats


def test_reflection_state_trend_rising_falling_flat_unknown():
    prev = AgentDayStats(name="Delta", role="optimizer", guardrail_count=5, context_count=5, avg_stress=0.10)

    # Rising (delta > EPS)
    cur_rise = AgentDayStats(name="Delta", role="optimizer", guardrail_count=5, context_count=5, avg_stress=0.12)
    rs_rise = derive_reflection_state(cur_rise, previous_stats=prev, supervisor_activity=0.0)
    assert rs_rise.stress_trend == "rising"

    # Falling (delta < -EPS)
    cur_fall = AgentDayStats(name="Delta", role="optimizer", guardrail_count=5, context_count=5, avg_stress=0.08)
    rs_fall = derive_reflection_state(cur_fall, previous_stats=prev, supervisor_activity=0.0)
    assert rs_fall.stress_trend == "falling"

    # Flat (within EPS band)
    cur_flat = AgentDayStats(name="Delta", role="optimizer", guardrail_count=5, context_count=5, avg_stress=0.105)
    rs_flat = derive_reflection_state(cur_flat, previous_stats=prev, supervisor_activity=0.0)
    assert rs_flat.stress_trend == "flat"

    # Unknown (no previous)
    cur_unknown = AgentDayStats(name="Delta", role="optimizer", guardrail_count=5, context_count=5, avg_stress=0.11)
    rs_unknown = derive_reflection_state(cur_unknown, previous_stats=None, supervisor_activity=0.0)
    assert rs_unknown.stress_trend == "unknown"


def test_reflection_state_rulebook_and_supervisor_presence_clamped():
    # Extreme counts -> reliance should clamp in [0,1]
    cur = AgentDayStats(name="Nova", role="qa", guardrail_count=10, context_count=0, avg_stress=0.2)
    rs = derive_reflection_state(cur, previous_stats=None, supervisor_activity=1.2)
    assert 0.0 <= rs.rulebook_reliance <= 1.0
    assert abs(rs.rulebook_reliance - 1.0) < 1e-6
    assert 0.0 <= rs.supervisor_presence <= 1.0
    assert abs(rs.supervisor_presence - 1.0) < 1e-6

    # Zero totals -> 0.0 reliance
    zero = AgentDayStats(name="Sprocket", role="maintenance", guardrail_count=0, context_count=0, avg_stress=0.0)
    rs0 = derive_reflection_state(zero, previous_stats=None, supervisor_activity=-0.5)
    assert abs(rs0.rulebook_reliance - 0.0) < 1e-6
    assert abs(rs0.supervisor_presence - 0.0) < 1e-6
