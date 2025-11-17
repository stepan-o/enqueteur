from __future__ import annotations

import json
from pathlib import Path
import pytest

from loopforge.analysis_api import analyze_episode


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
        # Identity fields (Sprint E3/E4)
        "run_id": run_id,
        "episode_id": episode_id,
    }


def test_analyze_episode_filters_by_ids(tmp_path: Path):
    # Build a JSONL with mixed runs/episodes. We'll analyze only run-B/ep-2.
    path = tmp_path / "actions.jsonl"
    lines: list[str] = []

    # Run A / Ep 1: steps 0..9 (day 0), agent Zeta context only
    for i in range(10):
        lines.append(json.dumps(_mk_line(i, "Zeta", "qa", "context", run_id="run-A", episode_id="ep-1")))

    # Run B / Ep 2: steps 0..9 (day 0), Delta guardrail only; Nova context only
    for i in range(10):
        lines.append(json.dumps(_mk_line(i, "Delta", "maintenance", "guardrail", run_id="run-B", episode_id="ep-2")))
        lines.append(json.dumps(_mk_line(i, "Nova", "qa", "context", run_id="run-B", episode_id="ep-2")))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Analyze only run-B/ep-2 for day 0
    ep = analyze_episode(
        action_log_path=path,
        steps_per_day=10,
        days=1,
        run_id="run-B",
        episode_id="ep-2",
    )

    assert len(ep.days) == 1
    d0 = ep.days[0]
    assert set(d0.agent_stats.keys()) == {"Delta", "Nova"}
    assert d0.agent_stats["Delta"].guardrail_count == 10
    assert d0.agent_stats["Nova"].guardrail_count == 0


def test_analyze_episode_missing_ids_raises(tmp_path: Path):
    # Minimal file (contents irrelevant since we expect an early error)
    p = tmp_path / "a.jsonl"
    p.write_text("\n", encoding="utf-8")

    with pytest.raises(ValueError) as ei:
        analyze_episode(action_log_path=p, steps_per_day=10, days=1)
    assert "requires run_id and episode_id" in str(ei.value)
