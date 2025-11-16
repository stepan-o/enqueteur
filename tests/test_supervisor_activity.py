from __future__ import annotations

from loopforge.supervisor_activity import compute_supervisor_activity
from loopforge.types import ActionLogEntry


def _mk_entry(step: int = 0) -> ActionLogEntry:
    return ActionLogEntry(
        step=step,
        agent_name="Supervisor",
        role="supervisor",
        mode="guardrail",
        intent="observe",
        move_to=None,
        targets=[],
        riskiness=0.0,
        narrative="",
        raw_action={},
        perception={},
        outcome=None,
    )


def test_empty_day_is_zero():
    assert compute_supervisor_activity([], steps_per_day=50) == 0.0


def test_half_steps_is_point5():
    entries = [_mk_entry(i) for i in range(25)]
    val = compute_supervisor_activity(entries, steps_per_day=50)
    assert abs(val - 0.5) < 1e-9


def test_clamps_above_one():
    entries = [_mk_entry(i) for i in range(200)]
    val = compute_supervisor_activity(entries, steps_per_day=50)
    assert abs(val - 1.0) < 1e-9


def test_zero_steps_is_zero():
    entries = [_mk_entry(i) for i in range(10)]
    assert compute_supervisor_activity(entries, steps_per_day=0) == 0.0
