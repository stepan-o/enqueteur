from __future__ import annotations

from loopforge.analytics.reporting import summarize_day, DaySummary, AgentDayStats
from loopforge.schema.types import ActionLogEntry
from loopforge.psych.attribution import derive_belief_attribution


def _mk_entry(step: int, name: str, role: str, mode: str, *, stress: float = 0.0, outcome: str | None = None):
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
        outcome=outcome,
    )


def test_summarize_day_populates_belief_attributions():
    # At least one agent with non-zero guardrail steps
    entries = [
        _mk_entry(0, "Delta", "optimizer", "guardrail", stress=0.12),
        _mk_entry(1, "Delta", "optimizer", "guardrail", stress=0.14),
        _mk_entry(2, "Delta", "optimizer", "context", stress=0.15),
    ]

    ds: DaySummary = summarize_day(day_index=0, entries=entries, reflections_by_agent=None)

    assert hasattr(ds, "belief_attributions"), "DaySummary should include belief_attributions field"
    assert isinstance(ds.belief_attributions, dict) and ds.belief_attributions, "belief_attributions should not be empty"
    assert "Delta" in ds.belief_attributions, "Belief attribution should be keyed by agent name"
    attr = ds.belief_attributions["Delta"]
    assert isinstance(attr.cause, str) and attr.cause, "Attribution cause should be a non-empty string"


def test_guardrail_cooling_system_attribution():
    # prev stress 0.30 -> current 0.10, no incidents, guardrail-heavy, low supervisor activity
    prev = AgentDayStats(name="Delta", role="optimizer", guardrail_count=100, context_count=0, avg_stress=0.30, incidents_nearby=0)
    cur = AgentDayStats(name="Delta", role="optimizer", guardrail_count=100, context_count=0, avg_stress=0.10, incidents_nearby=0)
    attr = derive_belief_attribution(cur, previous_stats=prev, supervisor_activity=0.2, tension=0.2)
    assert attr.cause == "system"
    assert attr.confidence >= 0.6


ess = 1e-6

def test_flat_day_random_attribution():
    prev = AgentDayStats(name="Delta", role="optimizer", guardrail_count=10, context_count=10, avg_stress=0.20, incidents_nearby=0)
    cur = AgentDayStats(name="Delta", role="optimizer", guardrail_count=10, context_count=10, avg_stress=0.20, incidents_nearby=0)
    attr = derive_belief_attribution(cur, previous_stats=prev, supervisor_activity=0.1, tension=0.2)
    assert attr.cause == "random"
    assert abs(attr.confidence - 0.2) < 1e-6
