from __future__ import annotations

import json
from pathlib import Path

from loopforge.core.logging_utils import JsonlActionLogger, log_action_step, read_action_log_entries
from loopforge.schema.types import AgentPerception, AgentActionPlan


def _mk_perception(step: int = 0, name: str = "Delta", role: str = "maintenance") -> AgentPerception:
    return AgentPerception(
        step=step,
        name=name,
        role=role,
        location="factory_floor",
        battery_level=100.0,
        emotions={"stress": 0.1, "curiosity": 0.5, "satisfaction": 0.5},
        traits={"guardrail_reliance": 0.5},
        world_summary="",
        personal_recent_summary="",
        local_events=[],
        recent_supervisor_text=None,
        extra={},
        perception_mode="accurate",
    )


def _mk_plan(mode: str = "guardrail") -> AgentActionPlan:
    return AgentActionPlan(
        intent="work",
        move_to=None,
        targets=[],
        riskiness=0.0,
        mode=mode,
        narrative="",
        meta={},
    )


def test_writer_adds_identity_fields_and_keeps_other_fields(tmp_path: Path):
    p = tmp_path / "actions.jsonl"
    logger = JsonlActionLogger(p)
    perc = _mk_perception(step=1)
    plan = _mk_plan(mode="context")

    log_action_step(
        logger=logger,
        perception=perc,
        plan=plan,
        action={"action_type": "move", "destination": "control_room"},
        outcome=None,
        run_id="run-abc",
        episode_id="ep-xyz",
        episode_index=3,
        day_index=0,
    )

    # Read raw line to check additive identity fields (reader ignores unknown keys by design)
    raw = p.read_text(encoding="utf-8").strip().splitlines()
    assert len(raw) == 1
    obj = json.loads(raw[0])
    assert obj.get("run_id") == "run-abc"
    assert obj.get("episode_id") == "ep-xyz"
    assert obj.get("episode_index") == 3
    # Ensure legacy fields remain intact
    assert obj["agent_name"] == "Delta"
    assert obj["mode"] == "context"
    assert obj["step"] == 1


def test_appending_one_line_and_loading_from_file_includes_identity_fields(tmp_path: Path):
    p = tmp_path / "actions.jsonl"
    logger = JsonlActionLogger(p)
    perc = _mk_perception(step=0, name="Nova", role="qa")
    plan = _mk_plan(mode="guardrail")

    log_action_step(
        logger=logger,
        perception=perc,
        plan=plan,
        action={"action_type": "work", "destination": "line_a"},
        outcome=None,
        run_id="run-123",
        episode_id="ep-456",
        episode_index=0,
        day_index=0,
    )

    # Raw load to assert identity triplet present in file
    line = p.read_text(encoding="utf-8").strip()
    obj = json.loads(line)
    assert obj.get("run_id") == "run-123"
    assert obj.get("episode_id") == "ep-456"
    assert obj.get("episode_index") == 0


def test_backward_compat_reader_accepts_old_line_without_ids(tmp_path: Path):
    # Construct an old-style line (no identity fields)
    old = {
        "step": 0,
        "agent_name": "Zeta",
        "role": "qa",
        "mode": "guardrail",
        "intent": "work",
        "move_to": None,
        "targets": [],
        "riskiness": 0.0,
        "narrative": "",
        "outcome": None,
        "raw_action": {},
        "perception": {"emotions": {"stress": 0.0}, "perception_mode": "accurate"},
        "policy_name": None,
        "episode_index": None,
        "day_index": 0,
    }
    p = tmp_path / "old.jsonl"
    p.write_text(json.dumps(old) + "\n", encoding="utf-8")

    # Reader should parse without exceptions and ignore missing identity fields
    entries = read_action_log_entries(p)
    assert len(entries) == 1
    e = entries[0]
    assert e.agent_name == "Zeta"
    assert e.mode == "guardrail"
    assert e.step == 0
