from __future__ import annotations

from pathlib import Path
import json

from loopforge.analysis_api import analyze_episode, episode_summary_to_dict
from loopforge.reporting import EpisodeSummary
from loopforge.types import ActionLogEntry


def _write_minimal_actions(path: Path, steps_per_day: int = 10) -> None:
    rows = []
    # Day 0: two guardrail steps for agent Delta (stress 0.3)
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
        perception={"emotions": {"stress": 0.30}, "perception_mode": "accurate"},
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
        perception={"emotions": {"stress": 0.30}, "perception_mode": "accurate"},
        outcome=None,
    ).to_dict())
    # Day 1: one guardrail step for Delta with lower stress (0.2)
    rows.append(ActionLogEntry(
        step=steps_per_day,
        agent_name="Delta",
        role="optimizer",
        mode="guardrail",
        intent="think",
        move_to=None,
        targets=[],
        riskiness=0.0,
        narrative="",
        raw_action={},
        perception={"emotions": {"stress": 0.20}, "perception_mode": "accurate"},
        outcome=None,
    ).to_dict())
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_trait_snapshot_exists_and_export_contains_snapshot(tmp_path: Path):
    actions_path = tmp_path / "actions.jsonl"
    _write_minimal_actions(actions_path, steps_per_day=10)

    ep: EpisodeSummary = analyze_episode(
        action_log_path=actions_path,
        supervisor_log_path=None,
        steps_per_day=10,
        days=2,
    )

    # Trait snapshot present for agent
    assert "Delta" in ep.agents
    snap = getattr(ep.agents["Delta"], "trait_snapshot", None)
    assert isinstance(snap, dict)
    # Contains five keys
    keys = set(snap.keys())
    assert keys == {"resilience", "caution", "agency", "trust_supervisor", "variance"}
    # All floats
    for v in snap.values():
        assert isinstance(v, float)

    # Deterministic export includes the snapshot
    export = episode_summary_to_dict(ep)
    assert "agents" in export and "Delta" in export["agents"]
    assert isinstance(export["agents"]["Delta"].get("trait_snapshot"), dict)
