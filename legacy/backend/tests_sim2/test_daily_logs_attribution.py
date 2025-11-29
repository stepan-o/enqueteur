from __future__ import annotations

from loopforge.analytics.reporting import DaySummary, AgentDayStats
from legacy.backend.loopforge_sim2 import build_daily_log
from loopforge.schema.types import BeliefAttribution


def test_daily_log_includes_attribution_bullet():
    stats = {"Delta": AgentDayStats(name="Delta", role="optimizer", guardrail_count=2, context_count=1, avg_stress=0.2)}
    ds = DaySummary(
        day_index=0,
        perception_mode="accurate",
        tension_score=0.2,
        agent_stats=stats,
        total_incidents=0,
    )
    ds.belief_attributions = {
        "Delta": BeliefAttribution(cause="system", confidence=0.6, rationale="test")
    }

    log = build_daily_log(ds, day_index=0, previous_day_summary=None)

    # Flatten lines for assertion
    text = "\n".join(["\n".join(v) for v in log.agent_beats.values()])
    assert "Attribution: system-driven (conf=0.60)." in text
