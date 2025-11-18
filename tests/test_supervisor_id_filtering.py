from __future__ import annotations

import json
from pathlib import Path
import pytest

from loopforge.analysis_api import analyze_episode
from loopforge.supervisor_activity import compute_supervisor_activity


RUN_A = "run-A"
EP_A0 = "ep-A0"
RUN_B = "run-B"
EP_B0 = "ep-B0"


def _mk_action(step: int, name: str, role: str, mode: str, *, run_id: str, episode_id: str) -> dict:
    return {
        "step": int(step),
        "agent_name": name,
        "role": role,
        "mode": mode,
        "intent": "work" if mode == "guardrail" else "inspect",
        "move_to": None,
        "targets": [],
        "riskiness": 0.0,
        "narrative": "",
        "outcome": None,
        "raw_action": {},
        "perception": {"emotions": {"stress": 0.0}, "perception_mode": "accurate"},
        "policy_name": None,
        "episode_index": 0,
        "day_index": step // 10,
        "run_id": run_id,
        "episode_id": episode_id,
    }


def _mk_sup_row(day_index: int, *, run_id: str, episode_id: str, body: str = "note") -> dict:
    return {
        "agent_name": "Delta",
        "role": "maintenance",
        "day_index": int(day_index),
        "intent": "neutral_update",
        "body": body,
        "episode_index": 0,
        "run_id": run_id,
        "episode_id": episode_id,
    }


def test_supervisor_logs_filtered_by_id(tmp_path: Path):
    actions_path = tmp_path / "actions.jsonl"
    supervisor_path = tmp_path / "supervisor.jsonl"

    # Write actions for two runs/episodes; we'll analyze only RUN_B/EP_B0.
    lines = []
    for i in range(10):
        lines.append(json.dumps(_mk_action(i, "Zeta", "qa", "context", run_id=RUN_A, episode_id=EP_A0)))
    for i in range(10):
        lines.append(json.dumps(_mk_action(i, "Delta", "maintenance", "guardrail", run_id=RUN_B, episode_id=EP_B0)))
    actions_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Supervisor rows: one for A/A0 (junk), two for B/B0 (target)
    sup_lines = [
        json.dumps(_mk_sup_row(0, run_id=RUN_A, episode_id=EP_A0, body="ignore")),
        json.dumps(_mk_sup_row(0, run_id=RUN_B, episode_id=EP_B0, body="keep-1")),
        json.dumps(_mk_sup_row(0, run_id=RUN_B, episode_id=EP_B0, body="keep-2")),
    ]
    supervisor_path.write_text("\n".join(sup_lines) + "\n", encoding="utf-8")

    ep = analyze_episode(
        action_log_path=actions_path,
        supervisor_log_path=supervisor_path,
        steps_per_day=10,
        days=1,
        run_id=RUN_B,
        episode_id=EP_B0,
    )

    # Day 0 supervisor activity should reflect exactly the two matching rows
    d0 = ep.days[0]
    expected = compute_supervisor_activity([
        _mk_sup_row(0, run_id=RUN_B, episode_id=EP_B0, body="keep-1"),
        _mk_sup_row(0, run_id=RUN_B, episode_id=EP_B0, body="keep-2"),
    ], steps_per_day=10)
    assert abs(float(d0.supervisor_activity) - float(expected)) < 1e-9


def test_supervisor_requires_ids(tmp_path: Path):
    actions_path = tmp_path / "actions.jsonl"
    supervisor_path = tmp_path / "supervisor.jsonl"

    # Minimal valid action row (IDs present)
    actions_path.write_text(json.dumps(_mk_action(0, "Delta", "maintenance", "guardrail", run_id=RUN_B, episode_id=EP_B0)) + "\n", encoding="utf-8")

    # ID-less supervisor row
    idless = {
        "agent_name": "Delta",
        "role": "maintenance",
        "day_index": 0,
        "intent": "neutral_update",
        "body": "missing ids",
        # no run_id / episode_id / episode_index
    }
    supervisor_path.write_text(json.dumps(idless) + "\n", encoding="utf-8")

    with pytest.raises(ValueError) as ei:
        analyze_episode(
            action_log_path=actions_path,
            supervisor_log_path=supervisor_path,
            steps_per_day=10,
            days=1,
            run_id=RUN_B,
            episode_id=EP_B0,
        )
    assert "Supervisor log entry missing run_id/episode_id" in str(ei.value)


def test_supervisor_logs_optional(tmp_path: Path):
    actions_path = tmp_path / "actions.jsonl"
    # Minimal valid actions for one day
    actions_path.write_text("\n".join(json.dumps(_mk_action(i, "Delta", "maintenance", "guardrail", run_id=RUN_B, episode_id=EP_B0)) for i in range(10)) + "\n", encoding="utf-8")

    # No supervisor log path -> should behave as before (no exceptions)
    ep = analyze_episode(
        action_log_path=actions_path,
        supervisor_log_path=None,
        steps_per_day=10,
        days=1,
        run_id=RUN_B,
        episode_id=EP_B0,
    )
    assert ep is not None and len(ep.days) == 1
