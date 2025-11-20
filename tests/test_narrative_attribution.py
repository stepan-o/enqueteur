from __future__ import annotations

from loopforge.reporting import DaySummary, AgentDayStats
from loopforge.narrative.narrative_viewer import build_day_narrative
from loopforge.schema.types import BeliefAttribution


def test_narrative_includes_attribution_sentence():
    # Minimal DaySummary with one agent and attribution
    stats = {"Delta": AgentDayStats(name="Delta", role="optimizer", guardrail_count=2, context_count=1, avg_stress=0.2)}
    ds = DaySummary(
        day_index=0,
        perception_mode="accurate",
        tension_score=0.2,
        agent_stats=stats,
        total_incidents=0,
    )
    # Inject attribution directly (simulates summarize_day having populated it)
    ds.belief_attributions = {
        "Delta": BeliefAttribution(cause="system", confidence=0.6, rationale="test")
    }

    dn = build_day_narrative(ds, day_index=0, previous_day_summary=None)

    # Render a flat text for assertion
    narrative_text = "\n".join([
        dn.day_intro,
        dn.supervisor_line,
        dn.day_outro,
    ] + [
        " ".join([b.intro, b.perception_line, b.actions_line, b.closing_line]) for b in dn.agent_beats
    ])

    assert "Delta seems to attribute today’s outcome to the system." in narrative_text
