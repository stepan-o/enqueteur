from __future__ import annotations

from backend.sim4.integration.diff_ops import apply_state_diff_ops, compute_state_diff_ops


def test_diff_ops_include_case_outcome_and_recap_singleton_updates() -> None:
    state_from = {
        "rooms": [],
        "agents": [],
        "items": [],
        "objects": [],
        "events": [],
        "case_outcome": {
            "truth_epoch": 1,
            "primary_outcome": "in_progress",
        },
        "case_recap": {
            "truth_epoch": 1,
            "available": False,
            "resolution_path": "in_progress",
        },
    }
    state_to = {
        "rooms": [],
        "agents": [],
        "items": [],
        "objects": [],
        "events": [],
        "case_outcome": {
            "truth_epoch": 1,
            "primary_outcome": "soft_fail",
        },
        "case_recap": {
            "truth_epoch": 1,
            "available": True,
            "resolution_path": "soft_fail",
        },
    }

    ops = compute_state_diff_ops(state_from, state_to)
    assert {"op": "SET_CASE_OUTCOME", "case_outcome": state_to["case_outcome"]} in ops
    assert {"op": "SET_CASE_RECAP", "case_recap": state_to["case_recap"]} in ops

    applied = apply_state_diff_ops(state_from, ops)
    assert applied["case_outcome"] == state_to["case_outcome"]
    assert applied["case_recap"] == state_to["case_recap"]
