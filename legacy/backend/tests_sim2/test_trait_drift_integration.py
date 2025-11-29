from __future__ import annotations

from pathlib import Path
import json

from loopforge.analytics.analysis_api import analyze_episode, episode_summary_to_dict
from loopforge.analytics.reporting import EpisodeSummary
from loopforge.schema.types import ActionLogEntry


RUN_ID = "run-test-trait-drift"
EPISODE_ID = "ep-test-trait-drift"
EPISODE_INDEX = 0


def _write_minimal_actions(path: Path, steps_per_day: int = 10) -> None:
    rows = []
    # Day 0: two guardrail steps for agent Delta (stress 0.3)
    for step in (0, 1):
        r = ActionLogEntry(
            step=step,
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
        ).to_dict()
        r["run_id"] = RUN_ID
        r["episode_id"] = EPISODE_ID
        r["episode_index"] = EPISODE_INDEX
        rows.append(r)

    # Day 1: one guardrail step for Delta with lower stress (0.2)
    r = ActionLogEntry(
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
    ).to_dict()
    r["run_id"] = RUN_ID
    r["episode_id"] = EPISODE_ID
    r["episode_index"] = EPISODE_INDEX
    rows.append(r)

    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_trait_snapshot_exists_and_export_contains_snapshot(tmp_path: Path):
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
