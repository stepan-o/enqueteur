from __future__ import annotations

import math
from typing import Optional

from loopforge.beliefs import derive_belief_state
from loopforge.reporting import AgentDayStats, DaySummary, summarize_day


def _mk_stats(name: str, role: str, g: int, c: int, s: float, incidents: int = 0) -> AgentDayStats:
    return AgentDayStats(name=name, role=role, guardrail_count=g, context_count=c, avg_stress=s, incidents_nearby=incidents)


def test_guardrail_faith_increases_guardrail_only_no_incidents():
    cur = _mk_stats("A", "qa", g=5, c=0, s=0.10, incidents=0)
    belief = derive_belief_state(agent_day_stats=cur, previous_stats=None, supervisor_activity=0.0, tension=0.2)
    assert belief.guardrail_faith > 0.5, "guardrail_faith should increase when guardrail-only with no incidents"


def test_self_efficacy_increases_context_only_no_incidents():
    cur = _mk_stats("A", "qa", g=0, c=5, s=0.10, incidents=0)
    belief = derive_belief_state(agent_day_stats=cur, previous_stats=None, supervisor_activity=0.0, tension=0.2)
    assert belief.self_efficacy > 0.5, "self_efficacy should increase when context-only with no incidents"


def test_supervisor_trust_decreases_when_active_and_stress_increases():
    prev = _mk_stats("A", "qa", g=1, c=1, s=0.10, incidents=0)
    cur = _mk_stats("A", "qa", g=1, c=1, s=0.25, incidents=0)
    # supervisor_activity high (>= 0.6)
    belief = derive_belief_state(agent_day_stats=cur, previous_stats=prev, supervisor_activity=0.8, tension=0.4)
    assert belief.supervisor_trust < 0.5, "supervisor_trust should decrease when supervisor is active and stress rises"


def test_day_summary_contains_beliefs_per_agent():
    # Build two minimal entries to feed summarize_day; ensure beliefs dict is populated
    from loopforge.types import ActionLogEntry

    entries = [
        ActionLogEntry(
            step=0,
            agent_name="Zeta",
            role="qa",
            mode="guardrail",
            intent="",
            move_to=None,
            targets=[],
            riskiness=0.0,
            narrative="",
            raw_action={},
            perception={"emotions": {"stress": 0.1}, "perception_mode": "accurate"},
            outcome=None,
        ),
        ActionLogEntry(
            step=1,
            agent_name="Zeta",
            role="qa",
            mode="guardrail",
            intent="",
            move_to=None,
            targets=[],
            riskiness=0.0,
            narrative="",
            raw_action={},
            perception={"emotions": {"stress": 0.12}, "perception_mode": "accurate"},
            outcome=None,
        ),
    ]

    ds: DaySummary = summarize_day(day_index=0, entries=entries, reflections_by_agent=None)
    assert hasattr(ds, "beliefs"), "DaySummary should include beliefs field"
    assert isinstance(ds.beliefs, dict)
    assert "Zeta" in ds.beliefs
