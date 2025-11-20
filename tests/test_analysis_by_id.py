from __future__ import annotations

import json
from pathlib import Path
import pytest

from loopforge.analytics.analysis_api import analyze_episode


def _mk_line(step: int, name: str, role: str, mode: str, *, run_id: str, episode_id: str) -> dict:
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


def test_analysis_filters_by_run_and_episode_id(tmp_path: Path):
    # Build a JSONL with mixed runs/episodes. We'll analyze only run-B/ep-B0.
    path = tmp_path / "actions.jsonl"
    lines: list[str] = []

    # Run A / Ep A0: steps 0..9 (day 0), agent Zeta context only
    for i in range(10):
        lines.append(json.dumps(_mk_line(i, "Zeta", "qa", "context", run_id="A", episode_id="A0")))

    # Run B / Ep B0: steps 0..9 (day 0), Delta guardrail only; Nova context only
    for i in range(10):
        lines.append(json.dumps(_mk_line(i, "Delta", "maintenance", "guardrail", run_id="B", episode_id="B0")))
        lines.append(json.dumps(_mk_line(i, "Nova", "qa", "context", run_id="B", episode_id="B0")))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ep = analyze_episode(
        action_log_path=path,
        steps_per_day=10,
        days=1,
        run_id="B",
        episode_id="B0",
    )

    assert len(ep.days) == 1
    d0 = ep.days[0]
    # Only Delta and Nova from run B / ep B0 should appear
    assert set(d0.agent_stats.keys()) == {"Delta", "Nova"}
    assert d0.agent_stats["Delta"].guardrail_count == 10
    assert d0.agent_stats["Nova"].guardrail_count == 0


def test_analysis_requires_matching_ids(tmp_path: Path):
    # Build a log with IDs that do not match the requested pair
    path = tmp_path / "actions.jsonl"
    line = _mk_line(0, "Delta", "maintenance", "guardrail", run_id="R1", episode_id="E1")
    path.write_text(json.dumps(line) + "\n", encoding="utf-8")

    with pytest.raises(ValueError) as ei:
        analyze_episode(action_log_path=path, steps_per_day=10, days=1, run_id="X", episode_id="Y")
    assert "No action log entries" in str(ei.value)


essential_id_keys = ("run_id", "episode_id")


def test_analysis_error_on_idless_rows(tmp_path: Path):
    # Write a row missing identity fields entirely
    path = tmp_path / "actions.jsonl"
    idless = {
        "step": 0,
        "agent_name": "Delta",
        "role": "maintenance",
        "mode": "guardrail",
        "intent": "work",
        "move_to": None,
        "targets": [],
        "riskiness": 0.0,
        "narrative": "",
        "outcome": None,
        "raw_action": {},
        "perception": {"emotions": {"stress": 0.0}, "perception_mode": "accurate"},
    }
    path.write_text(json.dumps(idless) + "\n", encoding="utf-8")

    with pytest.raises(ValueError) as ei:
        analyze_episode(action_log_path=path, steps_per_day=10, days=1, run_id="B", episode_id="B0")
    assert "requires IDs on all rows" in str(ei.value)
