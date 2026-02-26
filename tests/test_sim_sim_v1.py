from __future__ import annotations

import copy
import json

import pytest

from backend.sim_sim.config import ConfigValidationError, load_sim_sim_config
from backend.sim_sim.kernel.state import DayInput, PromptResponse, PromptState, SimSimKernel
from backend.sim_sim.projection.kvp_schema1 import compute_step_hash_for_channels, make_snapshot_payload


def _default_prompt_choice(prompt: PromptState) -> str:
    return str(prompt.choices[0])


def _advance_one_tick(
    kernel: SimSimKernel,
    tick_target: int,
    *,
    day_input: DayInput | None = None,
) -> None:
    active_input = day_input or DayInput(tick_target=tick_target, advance=True)
    valid, reason = kernel.validate_day_input(active_input, expected_tick_target=tick_target)
    assert valid, reason

    _, current = kernel.step(active_input)
    while int(current.day_tick) < int(tick_target):
        assert current.phase == "awaiting_prompts"
        unresolved = list(kernel.unresolved_prompts)
        assert unresolved, "awaiting_prompts must expose unresolved prompts"
        responses = tuple(
            PromptResponse(
                prompt_id=prompt.prompt_id,
                choice=_default_prompt_choice(prompt),
            )
            for prompt in unresolved
        )
        resolve_input = DayInput(
            tick_target=tick_target,
            advance=True,
            prompt_responses=responses,
        )
        valid, reason = kernel.validate_day_input(resolve_input, expected_tick_target=tick_target)
        assert valid, reason
        _, current = kernel.step(resolve_input)

    assert int(current.day_tick) == int(tick_target)
    assert current.phase == "planning"
    assert not kernel.unresolved_prompts


def _run_hashes(seed: int, days: int) -> list[str]:
    kernel = SimSimKernel(seed=seed)
    hashes: list[str] = []
    for day in range(1, days + 1):
        _advance_one_tick(kernel, tick_target=day)
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


def test_sim_sim_snapshot_hash_chain_matches_across_separate_runs() -> None:
    seed = 23
    channels = ["WORLD", "AGENTS", "ITEMS", "EVENTS"]

    kernel_a = SimSimKernel(seed=seed)
    kernel_b = SimSimKernel(seed=seed)

    run_context_a = {
        "seed": seed,
        "run_id": "run-A-uuid-like",
        "world_id": "world-A-uuid-like",
        "tick_hz": 1,
    }
    run_context_b = {
        "seed": seed,
        "run_id": "run-B-uuid-like",
        "world_id": "world-B-uuid-like",
        "tick_hz": 1,
    }

    hashes_a: list[str] = []
    hashes_b: list[str] = []

    # Baseline tick (0)
    snap_a = make_snapshot_payload(
        tick=kernel_a.state.day_tick,
        domain_state=kernel_a.state,
        channels=channels,
        run_context=run_context_a,
    )
    snap_b = make_snapshot_payload(
        tick=kernel_b.state.day_tick,
        domain_state=kernel_b.state,
        channels=channels,
        run_context=run_context_b,
    )
    hashes_a.append(str(snap_a["step_hash"]))
    hashes_b.append(str(snap_b["step_hash"]))

    # Advance 5 ticks with identical day inputs.
    for day in range(1, 6):
        _advance_one_tick(kernel_a, tick_target=day)
        _advance_one_tick(kernel_b, tick_target=day)
        snap_a = make_snapshot_payload(
            tick=kernel_a.state.day_tick,
            domain_state=kernel_a.state,
            channels=channels,
            run_context=run_context_a,
        )
        snap_b = make_snapshot_payload(
            tick=kernel_b.state.day_tick,
            domain_state=kernel_b.state,
            channels=channels,
            run_context=run_context_b,
        )
        hashes_a.append(str(snap_a["step_hash"]))
        hashes_b.append(str(snap_b["step_hash"]))

    assert hashes_a == hashes_b


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
        _advance_one_tick(kernel, tick_target=day)
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


def test_deferred_conflict_prompt_blocks_advance_until_resolved() -> None:
    kernel = SimSimKernel(seed=7)

    # Day 1 advances (conflict discovery may occur, but no unresolved prompt should remain).
    _advance_one_tick(kernel, tick_target=1)

    # Day 2 should produce a conflict prompt and stop at tick=1 awaiting resolution.
    day2_input = DayInput(tick_target=2, advance=True)
    valid, reason = kernel.validate_day_input(day2_input, expected_tick_target=2)
    assert valid, reason
    _, blocked = kernel.step(day2_input)
    assert blocked.day_tick == 1
    assert blocked.phase == "awaiting_prompts"
    unresolved = list(kernel.unresolved_prompts)
    assert unresolved
    assert any(prompt.kind == "conflict" for prompt in unresolved)

    # Attempting to advance without prompt responses is rejected.
    valid, reason = kernel.validate_day_input(DayInput(tick_target=2, advance=True), expected_tick_target=2)
    assert not valid
    assert "prompt_responses are required" in reason

    responses = tuple(
        PromptResponse(prompt_id=prompt.prompt_id, choice=_default_prompt_choice(prompt))
        for prompt in unresolved
    )
    resolve_input = DayInput(tick_target=2, advance=True, prompt_responses=responses)
    valid, reason = kernel.validate_day_input(resolve_input, expected_tick_target=2)
    assert valid, reason
    _, advanced = kernel.step(resolve_input)
    assert advanced.day_tick == 2
    assert advanced.phase == "planning"
    assert not kernel.unresolved_prompts
    assert any(
        event.get("kind") == "prompt_resolved" and event.get("details", {}).get("kind") == "conflict"
        for event in advanced.events
    )


def test_deferred_critical_prompt_blocks_advance_until_resolved(tmp_path) -> None:
    default_kernel = SimSimKernel(seed=5)
    config_raw = copy.deepcopy(default_kernel.loaded_config.raw)
    config_raw["conflicts"]["hostile_pairs"] = []
    config_raw["guardrails"]["prevent_critical_before_day"] = 0
    config_raw["confidence"]["threshold_critical"] = 0.0

    config_path = tmp_path / "critical_prompt_config.json"
    config_path.write_text(json.dumps(config_raw), encoding="utf-8")

    kernel = SimSimKernel(seed=5, config_path=str(config_path))
    day1_input = DayInput(tick_target=1, advance=True)
    valid, reason = kernel.validate_day_input(day1_input, expected_tick_target=1)
    assert valid, reason
    _, blocked = kernel.step(day1_input)

    assert blocked.day_tick == 0
    assert blocked.phase == "awaiting_prompts"
    unresolved = list(kernel.unresolved_prompts)
    assert unresolved
    assert any(prompt.kind == "critical" for prompt in unresolved)

    valid, reason = kernel.validate_day_input(DayInput(tick_target=1, advance=True), expected_tick_target=1)
    assert not valid
    assert "prompt_responses are required" in reason

    responses = tuple(
        PromptResponse(prompt_id=prompt.prompt_id, choice=_default_prompt_choice(prompt))
        for prompt in unresolved
    )
    resolve_input = DayInput(tick_target=1, advance=True, prompt_responses=responses)
    valid, reason = kernel.validate_day_input(resolve_input, expected_tick_target=1)
    assert valid, reason
    _, advanced = kernel.step(resolve_input)

    assert advanced.day_tick == 1
    assert advanced.phase == "planning"
    assert not kernel.unresolved_prompts
    assert any(
        event.get("kind") == "prompt_resolved" and event.get("details", {}).get("kind") == "critical"
        for event in advanced.events
    )


def test_sim_sim_config_loader_missing_fields_fails(tmp_path) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps({"metadata": {}}), encoding="utf-8")
    with pytest.raises(ConfigValidationError):
        load_sim_sim_config(bad_path)
