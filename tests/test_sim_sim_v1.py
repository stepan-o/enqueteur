from __future__ import annotations

import json

import pytest

from backend.sim_sim.config import ConfigValidationError, load_sim_sim_config
from backend.sim_sim.kernel.state import DayInput, SimSimKernel
from backend.sim_sim.projection.kvp_schema1 import compute_step_hash_for_channels


def _run_hashes(seed: int, days: int) -> list[str]:
    kernel = SimSimKernel(seed=seed)
    hashes: list[str] = []
    for day in range(1, days + 1):
        kernel.step(DayInput(tick_target=day, advance=True))
        hashes.append(
            compute_step_hash_for_channels(
                kernel.state,
                ["WORLD", "AGENTS", "ITEMS", "EVENTS"],
                run_context={
                    "seed": seed,
                    "run_id": "determinism",
                    "world_id": "determinism",
                    "tick_hz": 1,
                },
            )
        )
    return hashes


def test_sim_sim_determinism_same_seed_same_hashes() -> None:
    assert _run_hashes(seed=7, days=8) == _run_hashes(seed=7, days=8)


def test_sim_sim_determinism_different_seed_changes_hashes() -> None:
    assert _run_hashes(seed=7, days=6) != _run_hashes(seed=8, days=6)


def test_sim_sim_invariants_and_unlock_pacing() -> None:
    kernel = SimSimKernel(seed=11)
    cfg = kernel.loaded_config.config

    # Day0 canonical state.
    state0 = kernel.state
    assert state0.rooms[1].locked is False
    assert state0.rooms[2].locked is True
    assert state0.rooms[6].locked is True
    assert set(state0.supervisors.keys()) == {"L"}

    for day in range(1, 8):
        kernel.step(DayInput(tick_target=day, advance=True))
        state = kernel.state

        # Room 1 hard rule.
        room1 = state.rooms[1]
        assert room1.locked is False
        assert room1.workers_assigned_dumb is None
        assert room1.workers_assigned_smart is None
        assert room1.workers_present_dumb is None
        assert room1.workers_present_smart is None
        assert room1.casualties == 0

        # Room 6 hard rule.
        room6 = state.rooms[6]
        assert room6.locked is True
        assert room6.supervisor is None
        assert room6.workers_assigned_dumb is None
        assert room6.workers_assigned_smart is None
        assert room6.workers_present_dumb is None
        assert room6.workers_present_smart is None
        assert room6.casualties == 0

        # Unlock pacing expected from config.
        for room_id, unlock_day in cfg.unlock_schedule_rooms.items():
            if room_id == 6:
                assert state.rooms[room_id].locked is True
            elif day >= unlock_day:
                assert state.rooms[room_id].locked is False
            else:
                assert state.rooms[room_id].locked is True

        for code, unlock_day in cfg.unlock_schedule_supervisors.items():
            if day >= unlock_day:
                assert code in state.supervisors
            else:
                assert code not in state.supervisors

        # Capacity + inventory invariants.
        for room_id in (2, 3, 4, 5):
            room = state.rooms[room_id]
            if room.locked:
                continue
            cap = cfg.room_capacities[room_id]
            assigned_d = int(room.workers_assigned_dumb or 0)
            assigned_s = int(room.workers_assigned_smart or 0)
            assert assigned_d <= cap.max_dumb
            assert assigned_s <= cap.max_smart
            assert assigned_d + assigned_s <= cap.max_total

        for value in state.inventory.inventories.values():
            assert value >= 0
        assert state.inventory.cash >= 0

        events_today = [e for e in state.events if int(e.get("tick", -1)) == day]
        assert sum(1 for e in events_today if e.get("kind") == "conflict_event") <= 1
        assert sum(1 for e in events_today if e.get("kind") == "critical_triggered") <= 1


def test_sim_sim_config_loader_missing_fields_fails(tmp_path) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps({"metadata": {}}), encoding="utf-8")
    with pytest.raises(ConfigValidationError):
        load_sim_sim_config(bad_path)
