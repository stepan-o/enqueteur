from __future__ import annotations

import json
from pathlib import Path

from loopforge.day_runner import compute_day_summary
from loopforge.types import ActionLogEntry


def _mk_entry(step: int, name: str, role: str, mode: str):
    return ActionLogEntry(
        step=step,
        agent_name=name,
        role=role,
        mode=mode,
        intent="work",
        move_to=None,
        targets=[],
        riskiness=0.0,
        narrative="",
        raw_action={},
        perception={"emotions": {"stress": 0.0}, "perception_mode": "accurate"},
        outcome=None,
    )


def test_day_summary_counts_per_agent_and_day_isolated_to_latest_episode(tmp_path: Path):
    # Build a JSONL action log with two concatenated episodes to simulate append-only file.
    # Episode A (old): 1 day, 10 steps, single agent Zeta — should NOT influence results.
    # Episode B (latest): 2 days, 10 steps/day, two agents Delta and Nova.
    #   - Delta: guardrail every step
    #   - Nova: context every step (no guardrails)
    path = tmp_path / "actions.jsonl"
    lines: list[str] = []

    # Episode A (old) — steps 0..9 for agent Zeta
    for i in range(0, 10):
        e = _mk_entry(i, "Zeta", "qa", "context").to_dict()
        lines.append(json.dumps(e))

    # Episode B (latest) — Day 0: steps 0..9
    for i in range(0, 10):
        lines.append(json.dumps(_mk_entry(i, "Delta", "maintenance", "guardrail").to_dict()))
        lines.append(json.dumps(_mk_entry(i, "Nova", "qa", "context").to_dict()))

    # Episode B (latest) — Day 1: steps 10..19
    for i in range(10, 20):
        lines.append(json.dumps(_mk_entry(i, "Delta", "maintenance", "guardrail").to_dict()))
        lines.append(json.dumps(_mk_entry(i, "Nova", "qa", "context").to_dict()))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Compute Day 0 for latest episode
    ds0 = compute_day_summary(day_index=0, action_log_path=path, steps_per_day=10)
    # Expect only Delta and Nova, not Zeta; counts per agent per day
    assert set(ds0.agent_stats.keys()) == {"Delta", "Nova"}
    assert ds0.agent_stats["Delta"].guardrail_count == 10
    assert ds0.agent_stats["Nova"].guardrail_count == 0

    # Compute Day 1 for latest episode
    ds1 = compute_day_summary(day_index=1, action_log_path=path, steps_per_day=10)
    assert set(ds1.agent_stats.keys()) == {"Delta", "Nova"}
    assert ds1.agent_stats["Delta"].guardrail_count == 10
    assert ds1.agent_stats["Nova"].guardrail_count == 0
