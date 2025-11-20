from __future__ import annotations

from pathlib import Path

from loopforge.core.day_runner import compute_day_summary
from loopforge.reporting import DaySummary, AgentDayStats


def test_compute_day_summary_threads_supervisor_activity_into_reflection_state(tmp_path: Path):
    # Build a tiny JSONL action log for one day with one agent (no need to write supervisor logs)
    from loopforge.schema.types import ActionLogEntry
    import json

    actions_path = tmp_path / "actions.jsonl"
    rows = [
        ActionLogEntry(
            step=0,
            agent_name="Delta",
            role="optimizer",
            mode="guardrail",
            intent="work",
            move_to=None,
            targets=[],
            riskiness=0.0,
            narrative="",
            raw_action={},
            perception={"emotions": {"stress": 0.2}, "perception_mode": "accurate"},
            outcome=None,
        ).to_dict(),
        ActionLogEntry(
            step=1,
            agent_name="Delta",
            role="optimizer",
            mode="guardrail",
            intent="work",
            move_to=None,
            targets=[],
            riskiness=0.0,
            narrative="",
            raw_action={},
            perception={"emotions": {"stress": 0.2}, "perception_mode": "accurate"},
            outcome=None,
        ).to_dict(),
    ]
    actions_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    # Day 0: supervisor_activity = 0.0
    ds0: DaySummary = compute_day_summary(
        day_index=0,
        action_log_path=actions_path,
        steps_per_day=10,
        previous_day_stats=None,
        supervisor_activity=0.0,
    )
    assert isinstance(ds0, DaySummary)
    rs0 = ds0.reflection_states.get("Delta")
    assert rs0 is not None
    assert abs(rs0.supervisor_presence - 0.0) < 1e-9

    # Day 1: pass a non-zero supervisor_activity and ensure it appears in reflection state
    ds1: DaySummary = compute_day_summary(
        day_index=1,
        action_log_path=actions_path,
        steps_per_day=10,
        previous_day_stats=ds0.agent_stats,
        supervisor_activity=0.8,
    )
    rs1 = ds1.reflection_states.get("Delta")
    assert rs1 is not None
    assert abs(rs1.supervisor_presence - 0.8) < 1e-9
