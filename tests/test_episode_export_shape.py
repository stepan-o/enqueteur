from __future__ import annotations

from pathlib import Path
import json

from loopforge.analysis_api import analyze_episode, episode_summary_to_dict
from loopforge.reporting import EpisodeSummary
from loopforge.types import ActionLogEntry


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

    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_episode_export_shape_includes_blame_timelines_and_counts(tmp_path: Path):
    actions_path = tmp_path / "actions.jsonl"
    _write_minimal_actions(actions_path, steps_per_day=10)

    ep: EpisodeSummary = analyze_episode(
        action_log_path=actions_path,
        supervisor_log_path=None,
        steps_per_day=10,
        days=2,
    )

    export = episode_summary_to_dict(ep)
    # Top-level keys
    assert set(["days", "agents", "tension_trend"]).issubset(export.keys())

    # JSON serializable
    s = json.dumps(export)
    assert isinstance(s, str)

    # Per-agent derived fields
    assert export["agents"], "expected at least one agent"
    for name, block in export["agents"].items():
        assert "blame_timeline" in block
        assert "blame_counts" in block
        timeline = block["blame_timeline"]
        counts = block["blame_counts"]
        assert isinstance(timeline, list)
        assert isinstance(counts, dict)
        # counts should sum to length of timeline (including unknown)
        total = sum(int(v) for v in counts.values())
        assert total == len(timeline)
