from __future__ import annotations

from pathlib import Path
import json

from loopforge.analytics.analysis_api import analyze_episode
from loopforge.analytics.reporting import EpisodeSummary
from loopforge.schema.types import ActionLogEntry


RUN_ID = "test-run-001"
EPISODE_ID = "test-ep-001"
EPISODE_INDEX = 0


def _write_minimal_actions(path: Path, steps_per_day: int = 10) -> None:
    rows = []
    # Day 0: two guardrail steps for agent Delta
    rows.append(ActionLogEntry(
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
    ).to_dict())
    rows.append(ActionLogEntry(
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
    ).to_dict())
    # Day 1: one context step for Delta
    rows.append(ActionLogEntry(
        step=steps_per_day,
        agent_name="Delta",
        role="optimizer",
        mode="context",
        intent="think",
        move_to=None,
        targets=[],
        riskiness=0.0,
        narrative="",
        raw_action={},
        perception={"emotions": {"stress": 0.15}, "perception_mode": "accurate"},
        outcome=None,
    ).to_dict())

    # Inject IDs into every row (post–to_dict, like the real logger does)
    for r in rows:
        r["run_id"] = RUN_ID
        r["episode_id"] = EPISODE_ID
        r["episode_index"] = EPISODE_INDEX

    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_analyze_episode_returns_summary_with_days_and_agents(tmp_path: Path):
    actions_path = tmp_path / "actions.jsonl"
    _write_minimal_actions(actions_path, steps_per_day=10)

    ep: EpisodeSummary = analyze_episode(
        action_log_path=actions_path,
        supervisor_log_path=None,
        steps_per_day=10,
        days=2,
        run_id=RUN_ID,
        episode_id=EPISODE_ID,
        episode_index=EPISODE_INDEX,
    )

    assert isinstance(ep, EpisodeSummary)
    assert isinstance(ep.days, list)
    assert len(ep.days) == 2
    # At least one agent present across the episode
    assert ep.agents, "Expected at least one agent in episode summary"
    assert "Delta" in ep.agents
