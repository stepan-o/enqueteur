from __future__ import annotations

import copy
import json

import pytest

from backend.sim_sim.config import ConfigValidationError, load_sim_sim_config
from backend.sim_sim.kernel.state import (
    DayInput,
    PromptResponse,
    PromptState,
    SimSimKernel,
    SimSimState,
    SupervisorState,
    WorkerAssignment,
)
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


def _write_config(tmp_path, raw: dict, name: str) -> str:
    config_path = tmp_path / name
    config_path.write_text(json.dumps(raw), encoding="utf-8")
    return str(config_path)


def _set_supervisor_confidence_state(
    kernel: SimSimKernel,
    *,
    target_code: str,
    target_confidence: float,
    others_confidence: float,
    target_non_native: bool = False,
    target_cooldown_days: int = 0,
) -> None:
    state = kernel.state
    assignments = dict(state.assignments)
    supervisors: dict[str, SupervisorState] = {}

    for code, sup in state.supervisors.items():
        confidence = float(target_confidence if code == target_code else others_confidence)
        cooldown_days = int(target_cooldown_days if code == target_code else sup.cooldown_days)
        assigned_room = sup.native_room
        if code == "L":
            assigned_room = 1
        if code == target_code and target_non_native:
            assigned_room = 2 if sup.native_room != 2 else 3
        assignments[code] = assigned_room
        supervisors[code] = SupervisorState(
            code=sup.code,
            name=sup.name,
            unlocked_day=sup.unlocked_day,
            native_room=sup.native_room,
            assigned_room=assigned_room,
            loyalty=sup.loyalty,
            confidence=confidence,
            influence=sup.influence,
            cooldown_days=max(0, cooldown_days),
        )

    kernel._state = SimSimState(  # type: ignore[attr-defined]
        day_tick=state.day_tick,
        phase=state.phase,
        time_label=state.time_label,
        config_hash=state.config_hash,
        config_id=state.config_id,
        assignments=assignments,
        assignment_template=dict(state.assignment_template),
        rooms=dict(state.rooms),
        supervisors=supervisors,
        inventory=state.inventory,
        worker_pools=state.worker_pools,
        regime=state.regime,
        security_lead=state.security_lead,
        events=list(state.events),
        prompts=list(state.prompts),
        pending_day_input=state.pending_day_input,
        conflict=state.conflict,
        hidden_accumulators=state.hidden_accumulators,
        limen_security_count=state.limen_security_count,
        next_event_id=state.next_event_id,
    )


def _critical_test_kernel(tmp_path, *, seed: int = 7) -> SimSimKernel:
    base = SimSimKernel(seed=seed)
    cfg = copy.deepcopy(base.loaded_config.raw)
    cfg["conflicts"]["hostile_pairs"] = []
    cfg["guardrails"]["prevent_critical_before_day"] = 0
    cfg["confidence"]["threshold_critical"] = 1.0
    cfg["confidence"]["threshold_tension"] = 2.0
    cfg["confidence"]["native_bonus"] = 0.0
    cfg["confidence"]["base_drift_below_tension"] = 0.0
    cfg["confidence"]["non_native_no_success_penalty"] = 0.0
    cfg["confidence"]["unassigned_penalty"] = 0.0
    cfg["confidence"]["hated_penalty"] = 0.0
    cfg["confidence"]["tension_multiplier"] = 1.0
    cfg["confidence"]["outcome_delta"] = {
        "total_success": 0.0,
        "small_success": 0.0,
        "neutral": 0.0,
        "small_fiasco": 0.0,
        "total_fiasco": 0.0,
    }
    cfg["unlock_schedule"]["rooms"] = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 999}
    cfg["unlock_schedule"]["supervisors"] = {"L": 0, "S": 0, "C": 0, "W": 0, "T": 0}
    cfg["initial_state"]["worker_dumb"] = 40
    cfg["initial_state"]["worker_smart"] = 20
    cfg["guardrails"]["early_days_casualty_cap_until_day"] = 0
    cfg["formulas"]["absenteeism"] = {"base": 0.0, "stress_coeff": 0.0, "discipline_coeff": 0.0}
    cfg["formulas"]["accident"] = {"base": 0.0, "low_discipline_coeff": 0.0, "high_stress_coeff": 0.0, "low_equipment_coeff": 0.0}
    for key in list(cfg["worker_equations"].keys()):
        cfg["worker_equations"][key] = 0.0
    path = _write_config(tmp_path, cfg, "critical_test_config.json")
    return SimSimKernel(seed=seed, config_path=path)


def _trigger_critical_allow(kernel: SimSimKernel, *, tick_target: int, day_input: DayInput) -> None:
    valid, reason = kernel.validate_day_input(day_input, expected_tick_target=tick_target)
    assert valid, reason
    _, blocked = kernel.step(day_input)
    assert blocked.phase == "awaiting_prompts"
    prompt = next(p for p in kernel.unresolved_prompts if p.kind == "critical")
    resolve = DayInput(
        tick_target=tick_target,
        advance=True,
        prompt_responses=(PromptResponse(prompt_id=prompt.prompt_id, choice="allow"),),
    )
    valid, reason = kernel.validate_day_input(resolve, expected_tick_target=tick_target)
    assert valid, reason
    _, advanced = kernel.step(resolve)
    assert advanced.day_tick == tick_target
    assert advanced.phase == "planning"


def _outcome_row_test_kernel(tmp_path, *, seed: int = 11) -> SimSimKernel:
    base = SimSimKernel(seed=seed)
    cfg = copy.deepcopy(base.loaded_config.raw)
    cfg["conflicts"]["hostile_pairs"] = []
    cfg["guardrails"]["prevent_critical_before_day"] = 999
    cfg["confidence"]["threshold_critical"] = 2.0
    cfg["confidence"]["threshold_tension"] = 2.0
    cfg["confidence"]["native_bonus"] = 0.0
    cfg["confidence"]["base_drift_below_tension"] = 0.0
    cfg["confidence"]["non_native_no_success_penalty"] = 0.0
    cfg["confidence"]["unassigned_penalty"] = 0.0
    cfg["confidence"]["hated_penalty"] = 0.0
    cfg["confidence"]["tension_multiplier"] = 1.0
    cfg["confidence"]["outcome_delta"] = {
        "total_success": 0.0,
        "small_success": 0.0,
        "neutral": 0.0,
        "small_fiasco": 0.0,
        "total_fiasco": 0.0,
    }
    cfg["unlock_schedule"]["rooms"] = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 999}
    cfg["unlock_schedule"]["supervisors"] = {"L": 0, "S": 0, "C": 0, "W": 0, "T": 0}
    cfg["initial_state"]["worker_dumb"] = 20
    cfg["initial_state"]["worker_smart"] = 20
    cfg["guardrails"]["early_days_casualty_cap_until_day"] = 0
    cfg["formulas"]["absenteeism"] = {"base": 0.0, "stress_coeff": 0.0, "discipline_coeff": 0.0}
    cfg["formulas"]["accident"] = {"base": 0.0, "low_discipline_coeff": 0.0, "high_stress_coeff": 0.0, "low_equipment_coeff": 0.0}
    for key in list(cfg["worker_equations"].keys()):
        cfg["worker_equations"][key] = 0.0
    path = _write_config(tmp_path, cfg, f"outcome_row_test_{seed}.json")
    return SimSimKernel(seed=seed, config_path=path)


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


def test_limen_security_hours_penalty_caps_and_persists() -> None:
    kernel = SimSimKernel(seed=31)
    observed_hours: list[float] = []
    observed_counts: list[int] = []

    for day in range(1, 4):
        hours, _ = kernel._compute_hours(kernel.state, security_lead="L")  # type: ignore[attr-defined]
        observed_hours.append(hours)
        _advance_one_tick(kernel, tick_target=day)
        observed_counts.append(int(kernel.state.limen_security_count))

    assert observed_hours == [8.0, 7.0, 7.0]
    assert observed_counts == [1, 2, 3]


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


def test_factory_deltas_from_conflict_choice_affect_room_state(tmp_path) -> None:
    base_kernel = SimSimKernel(seed=7)
    config_raw = copy.deepcopy(base_kernel.loaded_config.raw)
    config_raw["guardrails"]["prevent_critical_before_day"] = 999
    config_raw["confidence"]["threshold_tension"] = 2.0
    for key in list(config_raw["worker_equations"].keys()):
        config_raw["worker_equations"][key] = 0.0

    config_path = _write_config(tmp_path, config_raw, "conflict_deltas_config.json")

    def _run(choice: str) -> SimSimKernel:
        kernel = SimSimKernel(seed=7, config_path=config_path)
        _advance_one_tick(kernel, tick_target=1)
        day2_input = DayInput(tick_target=2, advance=True)
        valid, reason = kernel.validate_day_input(day2_input, expected_tick_target=2)
        assert valid, reason
        _, blocked = kernel.step(day2_input)
        assert blocked.phase == "awaiting_prompts"
        prompt = next(p for p in kernel.unresolved_prompts if p.kind == "conflict")
        resolve_input = DayInput(
            tick_target=2,
            advance=True,
            prompt_responses=(PromptResponse(prompt_id=prompt.prompt_id, choice=choice),),
        )
        valid, reason = kernel.validate_day_input(resolve_input, expected_tick_target=2)
        assert valid, reason
        _, advanced = kernel.step(resolve_input)
        assert advanced.day_tick == 2
        return kernel

    state_support_a = _run("support_A").state
    state_support_b = _run("support_B").state

    room2_a = state_support_a.rooms[2]
    room2_b = state_support_b.rooms[2]
    assert float(room2_b.stress or 0.0) > float(room2_a.stress or 0.0)
    assert float(room2_a.discipline or 0.0) > float(room2_b.discipline or 0.0)
    assert float(room2_a.alignment or 0.0) > float(room2_b.alignment or 0.0)


def test_factory_global_accident_bonus_delta_affects_accident_outcome(tmp_path) -> None:
    base_kernel = SimSimKernel(seed=2)

    def _run_with_bonus(global_bonus: float) -> SimSimKernel:
        config_raw = copy.deepcopy(base_kernel.loaded_config.raw)
        config_raw["guardrails"]["prevent_critical_before_day"] = 999
        config_raw["conflicts"]["hostile_pairs"] = []
        config_raw["formulas"]["accident"] = {
            "base": 0.0,
            "low_discipline_coeff": 0.0,
            "high_stress_coeff": 0.0,
            "low_equipment_coeff": 0.0,
        }
        config_raw["formulas"]["absenteeism"] = {
            "base": 0.0,
            "stress_coeff": 0.0,
            "discipline_coeff": 0.0,
        }
        config_raw["confidence"]["threshold_tension"] = 0.0
        config_raw["confidence"]["tension_passives"] = {
            "L": {"global_accident_bonus": float(global_bonus)},
            "S": {},
            "C": {},
            "W": {},
            "T": {},
        }
        config_raw["unlock_schedule"]["rooms"]["2"] = 0
        config_raw["unlock_schedule"]["supervisors"]["S"] = 999
        config_raw["unlock_schedule"]["supervisors"]["C"] = 999
        config_raw["unlock_schedule"]["supervisors"]["W"] = 999
        config_raw["unlock_schedule"]["supervisors"]["T"] = 999

        config_path = _write_config(
            tmp_path,
            config_raw,
            f"accident_bonus_{str(global_bonus).replace('.', '_')}.json",
        )
        kernel = SimSimKernel(seed=2, config_path=config_path)
        day_input = DayInput(
            tick_target=1,
            advance=True,
            set_workers={2: WorkerAssignment(dumb=1, smart=0)},
        )
        _advance_one_tick(kernel, tick_target=1, day_input=day_input)
        return kernel

    without_bonus = _run_with_bonus(0.0).state
    with_bonus = _run_with_bonus(0.5).state

    assert without_bonus.rooms[2].accidents_count == 0
    assert with_bonus.rooms[2].accidents_count >= 1


def test_outcome_row_loyalty_delta_updates_supervisor_loyalty(tmp_path) -> None:
    base = _outcome_row_test_kernel(tmp_path, seed=61)
    config_raw = copy.deepcopy(base.loaded_config.raw)
    config_raw["outcome_tables"]["S"]["2"] = [
        {
            "label": "neutral",
            "weight": 1,
            "sup_mult": 1.0,
            "fiasco_severity": 0.0,
            "loyalty_delta": 0.2,
        }
    ]
    config_path = _write_config(tmp_path, config_raw, "outcome_loyalty_delta.json")
    kernel = SimSimKernel(seed=61, config_path=config_path)

    day_input = DayInput(
        tick_target=1,
        advance=True,
        set_supervisors={2: "S"},
        set_workers={2: WorkerAssignment(dumb=4, smart=2)},
    )
    _advance_one_tick(kernel, tick_target=1, day_input=day_input)
    assert abs(float(kernel.state.supervisors["S"].loyalty) - 0.75) < 1e-9


def test_outcome_row_weaving_boost_applies_next_day_only(tmp_path) -> None:
    base = _outcome_row_test_kernel(tmp_path, seed=67)
    config_boost = copy.deepcopy(base.loaded_config.raw)
    config_boost["outcome_tables"]["S"]["2"] = [
        {
            "label": "neutral",
            "weight": 1,
            "sup_mult": 1.0,
            "fiasco_severity": 0.0,
            "weaving_boost_next_day": 3.0,
        }
    ]
    config_boost["outcome_tables"]["C"]["5"] = [
        {
            "label": "neutral",
            "weight": 1,
            "sup_mult": 1.0,
            "fiasco_severity": 0.0,
        }
    ]
    config_control = copy.deepcopy(base.loaded_config.raw)
    config_control["outcome_tables"]["S"]["2"] = [
        {
            "label": "neutral",
            "weight": 1,
            "sup_mult": 1.0,
            "fiasco_severity": 0.0,
            "weaving_boost_next_day": 1.0,
        }
    ]
    config_control["outcome_tables"]["C"]["5"] = [
        {
            "label": "neutral",
            "weight": 1,
            "sup_mult": 1.0,
            "fiasco_severity": 0.0,
        }
    ]
    boost_path = _write_config(tmp_path, config_boost, "outcome_weaving_boost.json")
    control_path = _write_config(tmp_path, config_control, "outcome_weaving_control.json")

    def _run_two_days(config_path: str) -> tuple[int, int]:
        kernel = SimSimKernel(seed=67, config_path=config_path)
        day1 = DayInput(
            tick_target=1,
            advance=True,
            set_supervisors={2: "S", 5: "C"},
            set_workers={2: WorkerAssignment(dumb=4, smart=2), 5: WorkerAssignment(dumb=0, smart=3)},
        )
        _advance_one_tick(kernel, tick_target=1, day_input=day1)
        ribbon_day1 = int(kernel.state.rooms[5].output_today["ribbon_yards"])
        day2 = DayInput(
            tick_target=2,
            advance=True,
            set_supervisors={2: "S", 5: "C"},
            set_workers={2: WorkerAssignment(dumb=4, smart=2), 5: WorkerAssignment(dumb=0, smart=3)},
        )
        _advance_one_tick(kernel, tick_target=2, day_input=day2)
        ribbon_day2 = int(kernel.state.rooms[5].output_today["ribbon_yards"])
        return ribbon_day1, ribbon_day2

    boost_day1, boost_day2 = _run_two_days(boost_path)
    control_day1, control_day2 = _run_two_days(control_path)

    assert boost_day1 == control_day1
    assert boost_day2 > control_day2


def test_outcome_row_keys_are_all_consumed_or_intentionally_structural() -> None:
    kernel = SimSimKernel(seed=5)
    row_keys: set[str] = set()
    for _, by_room in kernel.loaded_config.raw.get("outcome_tables", {}).items():
        for _, rows in by_room.items():
            for row in rows:
                if isinstance(row, dict):
                    row_keys.update(str(k) for k in row.keys())

    consumed_keys = {
        "label",
        "weight",
        "sup_mult",
        "fiasco_severity",
        "no_accidents",
        "casualties_min",
        "casualties_max",
        "equipment_damage_min",
        "equipment_damage_max",
        "repair_all_equipment",
        "repair_first",
        "factory_stress_delta",
        "factory_discipline_delta",
        "factory_alignment_delta",
        "weaving_boost_next_day",
        "loyalty_delta",
    }
    assert row_keys.issubset(consumed_keys)


def test_critical_event_w_applies_shutdown_brewery_multiplier_and_refactor_duration(tmp_path) -> None:
    kernel = _critical_test_kernel(tmp_path, seed=17)
    _set_supervisor_confidence_state(kernel, target_code="W", target_confidence=1.0, others_confidence=0.0)

    day_input = DayInput(
        tick_target=1,
        advance=True,
        set_workers={
            2: WorkerAssignment(dumb=6, smart=2),
            3: WorkerAssignment(dumb=4, smart=1),
            4: WorkerAssignment(dumb=1, smart=3),
            5: WorkerAssignment(dumb=0, smart=3),
        },
    )
    _trigger_critical_allow(kernel, tick_target=1, day_input=day_input)
    state = kernel.state

    assert sum(state.rooms[2].output_today.values()) == 0
    assert sum(state.rooms[3].output_today.values()) == 0
    assert sum(state.rooms[5].output_today.values()) == 0
    assert state.rooms[4].output_today["substrate_gallons"] > 0
    for room_id in (2, 3, 4, 5):
        assert float(state.rooms[room_id].equipment_condition or 0.0) == 1.0
    assert state.regime.refactor_days == 2
    assert state.regime.global_accident_bonus >= 0.15


def test_critical_event_t_applies_inversion_and_output_modifiers(tmp_path) -> None:
    kernel = _critical_test_kernel(tmp_path, seed=19)
    _set_supervisor_confidence_state(kernel, target_code="T", target_confidence=1.0, others_confidence=0.0)

    day_input = DayInput(
        tick_target=1,
        advance=True,
        set_workers={
            2: WorkerAssignment(dumb=6, smart=2),
            3: WorkerAssignment(dumb=4, smart=1),
            4: WorkerAssignment(dumb=1, smart=3),
            5: WorkerAssignment(dumb=0, smart=3),
        },
    )
    _trigger_critical_allow(kernel, tick_target=1, day_input=day_input)
    state = kernel.state

    assert sum(state.rooms[5].output_today.values()) == 0
    assert state.regime.inversion_days == 1
    assert state.regime.global_accident_bonus >= 0.05
    assert float(state.rooms[2].stress or 0.0) <= 0.1
    assert float(state.rooms[2].discipline or 0.0) <= 0.2


def test_critical_event_l_applies_factory_lockdown_and_metric_deltas(tmp_path) -> None:
    kernel = _critical_test_kernel(tmp_path, seed=23)
    _set_supervisor_confidence_state(kernel, target_code="L", target_confidence=1.0, others_confidence=0.0)

    day_input = DayInput(
        tick_target=1,
        advance=True,
        set_workers={
            2: WorkerAssignment(dumb=6, smart=2),
            3: WorkerAssignment(dumb=4, smart=1),
            4: WorkerAssignment(dumb=1, smart=3),
            5: WorkerAssignment(dumb=0, smart=3),
        },
    )
    _trigger_critical_allow(kernel, tick_target=1, day_input=day_input)
    state = kernel.state

    assert sum(state.rooms[2].output_today.values()) == 0
    assert sum(state.rooms[3].output_today.values()) == 0
    assert sum(state.rooms[4].output_today.values()) == 0
    assert sum(state.rooms[5].output_today.values()) == 0
    assert float(state.rooms[2].discipline or 0.0) >= 0.70
    assert float(state.rooms[2].stress or 0.0) >= 0.18


def test_critical_event_s_applies_conveyor_casualties_and_equipment_override(tmp_path) -> None:
    kernel = _critical_test_kernel(tmp_path, seed=29)
    _set_supervisor_confidence_state(kernel, target_code="S", target_confidence=1.0, others_confidence=0.0)

    day_input = DayInput(
        tick_target=1,
        advance=True,
        set_workers={
            2: WorkerAssignment(dumb=6, smart=2),
            3: WorkerAssignment(dumb=4, smart=1),
            4: WorkerAssignment(dumb=1, smart=3),
            5: WorkerAssignment(dumb=0, smart=3),
        },
    )
    _trigger_critical_allow(kernel, tick_target=1, day_input=day_input)
    state = kernel.state

    assert 3 <= int(state.rooms[2].casualties) <= 6
    assert float(state.rooms[2].equipment_condition or 1.0) == 0.0
    assert state.rooms[2].output_today["raw_brains_dumb"] + state.rooms[2].output_today["raw_brains_smart"] >= 0


def test_critical_event_c_sets_all_room_alignment(tmp_path) -> None:
    kernel = _critical_test_kernel(tmp_path, seed=31)
    _set_supervisor_confidence_state(kernel, target_code="C", target_confidence=1.0, others_confidence=0.0)

    day_input = DayInput(
        tick_target=1,
        advance=True,
        set_workers={
            2: WorkerAssignment(dumb=6, smart=2),
            3: WorkerAssignment(dumb=4, smart=1),
            4: WorkerAssignment(dumb=1, smart=3),
            5: WorkerAssignment(dumb=0, smart=3),
        },
    )
    _trigger_critical_allow(kernel, tick_target=1, day_input=day_input)
    state = kernel.state

    for room_id in (2, 3, 4, 5):
        assert float(state.rooms[room_id].alignment or 1.0) == 0.0


def test_critical_duration_counters_decrement_and_expire(tmp_path) -> None:
    kernel = _critical_test_kernel(tmp_path, seed=37)
    _set_supervisor_confidence_state(kernel, target_code="W", target_confidence=1.0, others_confidence=0.0)

    day1_input = DayInput(
        tick_target=1,
        advance=True,
        set_workers={
            2: WorkerAssignment(dumb=6, smart=2),
            3: WorkerAssignment(dumb=4, smart=1),
            4: WorkerAssignment(dumb=1, smart=3),
            5: WorkerAssignment(dumb=0, smart=3),
        },
    )
    _trigger_critical_allow(kernel, tick_target=1, day_input=day1_input)
    assert kernel.state.regime.refactor_days == 2

    _set_supervisor_confidence_state(kernel, target_code="W", target_confidence=0.0, others_confidence=0.0)
    _advance_one_tick(kernel, tick_target=2, day_input=DayInput(tick_target=2, advance=True))
    assert kernel.state.regime.refactor_days == 1
    _advance_one_tick(kernel, tick_target=3, day_input=DayInput(tick_target=3, advance=True))
    assert kernel.state.regime.refactor_days == 0


def test_critical_prompt_gating_respects_guardrail_threshold_cooldown_and_native_room(tmp_path) -> None:
    # guardrail blocks even with high confidence
    kernel_guardrail = _critical_test_kernel(tmp_path, seed=41)
    cfg_guardrail = copy.deepcopy(kernel_guardrail.loaded_config.raw)
    cfg_guardrail["guardrails"]["prevent_critical_before_day"] = 5
    path_guardrail = _write_config(tmp_path, cfg_guardrail, "critical_guardrail_config.json")
    kernel_guardrail = SimSimKernel(seed=41, config_path=path_guardrail)
    _set_supervisor_confidence_state(kernel_guardrail, target_code="L", target_confidence=1.0, others_confidence=0.0)
    _, state_guardrail = kernel_guardrail.step(DayInput(tick_target=1, advance=True))
    assert state_guardrail.phase == "planning"

    # below-threshold confidence does not prompt
    kernel_threshold = _critical_test_kernel(tmp_path, seed=43)
    _set_supervisor_confidence_state(kernel_threshold, target_code="S", target_confidence=0.2, others_confidence=0.0)
    _, state_threshold = kernel_threshold.step(DayInput(tick_target=1, advance=True))
    assert state_threshold.phase == "planning"

    # cooldown blocks prompt
    kernel_cooldown = _critical_test_kernel(tmp_path, seed=47)
    _set_supervisor_confidence_state(
        kernel_cooldown,
        target_code="C",
        target_confidence=1.0,
        others_confidence=0.0,
        target_cooldown_days=1,
    )
    _, state_cooldown = kernel_cooldown.step(DayInput(tick_target=1, advance=True))
    assert state_cooldown.phase == "planning"

    # non-native assignment blocks prompt
    kernel_non_native = _critical_test_kernel(tmp_path, seed=53)
    _set_supervisor_confidence_state(
        kernel_non_native,
        target_code="T",
        target_confidence=1.0,
        others_confidence=0.0,
        target_non_native=True,
    )
    _, state_non_native = kernel_non_native.step(DayInput(tick_target=1, advance=True))
    assert state_non_native.phase == "planning"


def test_sim_sim_config_loader_missing_fields_fails(tmp_path) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps({"metadata": {}}), encoding="utf-8")
    with pytest.raises(ConfigValidationError):
        load_sim_sim_config(bad_path)
