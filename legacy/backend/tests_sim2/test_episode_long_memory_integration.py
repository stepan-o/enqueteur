from __future__ import annotations

from pathlib import Path
import json

from loopforge.analytics.analysis_api import analyze_episode, episode_summary_to_dict
from loopforge.analytics.reporting import EpisodeSummary
from loopforge.schema.types import ActionLogEntry


RUN_ID = "run-test-long-memory"
EPISODE_ID = "ep-test-long-memory"
EPISODE_INDEX = 0


def _write_minimal_actions(path: Path, steps_per_day: int = 10) -> None:
    rows = []
    # Day 0: two guardrail steps for agent Delta
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
            perception={"emotions": {"stress": 0.2}, "perception_mode": "accurate"},
            outcome=None,
        ).to_dict()
        r["run_id"] = RUN_ID
        r["episode_id"] = EPISODE_ID
        r["episode_index"] = EPISODE_INDEX
        rows.append(r)

    # Day 1: one context step for Delta (slightly lower stress)
    r = ActionLogEntry(
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
    ).to_dict()
    r["run_id"] = RUN_ID
    r["episode_id"] = EPISODE_ID
    r["episode_index"] = EPISODE_INDEX
    rows.append(r)

    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


essentials = [
    (10, 2),
]


def test_episode_summary_includes_long_memory(tmp_path: Path):
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
    # Long memory should be attached (additive)
    assert hasattr(ep, "long_memory")
    assert ep.long_memory is None or isinstance(ep.long_memory, dict)
    # If present, it should contain entries for known agents with [0,1] identity axes
    if isinstance(ep.long_memory, dict) and ep.long_memory:
        assert "Delta" in ep.long_memory
        mem = ep.long_memory["Delta"]
        for v in [mem.trust_supervisor, mem.self_trust, mem.stability, mem.reactivity, mem.agency]:
            assert 0.0 <= float(v) <= 1.0


def test_episode_export_includes_long_memory_key(tmp_path: Path):
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

    out = episode_summary_to_dict(ep)
    assert "long_memory" in out
    # JSON-serializable
    s = json.dumps(out)
    assert isinstance(s, str)
    lm = out["long_memory"]
    assert lm is None or isinstance(lm, dict)
    if isinstance(lm, dict) and lm:
        # Check required inner keys for one agent
        sample = next(iter(lm.values()))
        required = {
            "episodes",
            "cumulative_stress",
            "cumulative_incidents",
            "trust_supervisor",
            "self_trust",
            "stability",
            "reactivity",
            "agency",
        }
        assert required.issubset(sample.keys())
