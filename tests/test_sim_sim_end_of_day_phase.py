from __future__ import annotations

import copy
import json

from backend.sim_sim.kernel.state import DayInput, EndOfDayActions, PromptResponse, SimSimKernel


def _write_config(tmp_path, raw: dict, name: str) -> str:
    config_path = tmp_path / name
    config_path.write_text(json.dumps(raw), encoding="utf-8")
    return str(config_path)


def _kernel_without_prompts(
    tmp_path,
    *,
    seed: int = 7,
    cash: int | None = None,
    inventory_overrides: dict[str, int] | None = None,
) -> SimSimKernel:
    base = SimSimKernel(seed=seed)
    config_raw = copy.deepcopy(base.loaded_config.raw)
    config_raw["conflicts"]["hostile_pairs"] = []
    config_raw["guardrails"]["prevent_critical_before_day"] = 999
    if cash is not None:
        config_raw["initial_state"]["cash"] = int(cash)
    if inventory_overrides:
        for key, value in inventory_overrides.items():
            config_raw["initial_state"]["inventory"][str(key)] = int(value)
    config_path = _write_config(tmp_path, config_raw, "end_of_day_phase_config.json")
    return SimSimKernel(seed=seed, config_path=config_path)


def _kernel_with_forced_prompt(tmp_path) -> SimSimKernel:
    base = SimSimKernel(seed=5)
    config_raw = copy.deepcopy(base.loaded_config.raw)
    config_raw["conflicts"]["hostile_pairs"] = []
    config_raw["guardrails"]["prevent_critical_before_day"] = 0
    config_raw["confidence"]["threshold_critical"] = 0.0
    config_path = _write_config(tmp_path, config_raw, "forced_prompt_config.json")
    return SimSimKernel(seed=5, config_path=config_path)


def test_planning_without_prompts_enters_end_of_day_phase(tmp_path) -> None:
    kernel = _kernel_without_prompts(
        tmp_path,
        cash=50,
        inventory_overrides={"washed_dumb": 3},
    )
    planning_input = DayInput(tick_target=1, advance=True)
    start_cash = kernel.state.inventory.cash
    start_washed_dumb = int(kernel.state.inventory.inventories.get("washed_dumb", 0))
    start_raw_dumb = int(kernel.state.inventory.inventories.get("raw_brains_dumb", 0))

    valid, reason = kernel.validate_day_input(planning_input, expected_tick_target=1)
    assert valid, reason

    previous, current = kernel.step(planning_input)

    assert previous.day_tick == 0
    assert current.day_tick == 0
    assert current.phase == "end_of_day"
    assert not kernel.unresolved_prompts
    # The resolved day is preserved for UI/EOD display.
    assert current.rooms[2].locked is False
    assert int(current.inventory.inventories.get("raw_brains_dumb", 0)) > start_raw_dumb
    # No EOD application yet while gated in end_of_day.
    assert current.inventory.cash == start_cash
    assert int(current.inventory.inventories.get("washed_dumb", 0)) == start_washed_dumb
    event_kinds = [str(event.get("kind", "")) for event in current.events]
    assert "eod_opened" in event_kinds
    assert "eod_upgrade" not in event_kinds
    assert "eod_sell" not in event_kinds
    assert "eod_convert" not in event_kinds


def test_resolved_prompts_transition_to_end_of_day_phase(tmp_path) -> None:
    kernel = _kernel_with_forced_prompt(tmp_path)
    planning_input = DayInput(tick_target=1, advance=True)
    valid, reason = kernel.validate_day_input(planning_input, expected_tick_target=1)
    assert valid, reason

    _, awaiting = kernel.step(planning_input)
    assert awaiting.day_tick == 0
    assert awaiting.phase == "awaiting_prompts"
    unresolved = list(kernel.unresolved_prompts)
    assert unresolved

    resolve_input = DayInput(
        tick_target=1,
        advance=True,
        prompt_responses=tuple(
            PromptResponse(
                prompt_id=prompt.prompt_id,
                choice=str(prompt.choices[0]),
            )
            for prompt in unresolved
        ),
    )
    valid, reason = kernel.validate_day_input(resolve_input, expected_tick_target=1)
    assert valid, reason
    _, gated = kernel.step(resolve_input)
    assert gated.day_tick == 0
    assert gated.phase == "end_of_day"
    assert not kernel.unresolved_prompts


def test_end_of_day_blocks_new_planning_inputs_until_eod_apply(tmp_path) -> None:
    kernel = _kernel_without_prompts(tmp_path)
    planning_input = DayInput(tick_target=1, advance=True)
    valid, reason = kernel.validate_day_input(planning_input, expected_tick_target=1)
    assert valid, reason
    _, current = kernel.step(planning_input)
    assert current.phase == "end_of_day"

    invalid_planning_input = DayInput(
        tick_target=1,
        advance=True,
        set_supervisors={1: "L"},
    )
    valid, reason = kernel.validate_day_input(invalid_planning_input, expected_tick_target=1)
    assert not valid
    assert "only end_of_day actions are accepted" in reason
    assert kernel.state.day_tick == 0
    assert kernel.state.phase == "end_of_day"


def test_end_of_day_input_applies_actions_and_advances_day(tmp_path) -> None:
    kernel = _kernel_without_prompts(
        tmp_path,
        cash=50,
        inventory_overrides={"washed_dumb": 3},
    )
    planning_input = DayInput(tick_target=1, advance=True)
    valid, reason = kernel.validate_day_input(planning_input, expected_tick_target=1)
    assert valid, reason
    _, eod_state = kernel.step(planning_input)
    assert eod_state.phase == "end_of_day"
    assert eod_state.day_tick == 0

    sell_count = 2
    eod_input = DayInput(
        tick_target=1,
        advance=True,
        end_of_day=EndOfDayActions(sell_washed_dumb=sell_count),
    )
    valid, reason = kernel.validate_day_input(eod_input, expected_tick_target=1)
    assert valid, reason
    previous, current = kernel.step(eod_input)

    assert previous.phase == "end_of_day"
    assert current.day_tick == 1
    assert current.phase == "planning"
    expected_cash = eod_state.inventory.cash + (sell_count * kernel.loaded_config.config.economy.sell_washed_dumb)
    assert current.inventory.cash == expected_cash
    assert int(current.inventory.inventories.get("washed_dumb", 0)) == int(eod_state.inventory.inventories.get("washed_dumb", 0)) - sell_count

    event_kinds = [str(event.get("kind", "")) for event in current.events]
    assert "eod_sell" in event_kinds
    assert "eod_confirmed" in event_kinds
    assert event_kinds.index("eod_sell") < event_kinds.index("eod_confirmed")


def test_end_of_day_applies_upgrade_sell_convert_in_order(tmp_path) -> None:
    kernel = _kernel_without_prompts(
        tmp_path,
        cash=50,
        inventory_overrides={
            "washed_dumb": 20,
            "washed_smart": 10,
            "substrate_gallons": 3,
            "ribbon_yards": 3,
        },
    )
    planning_input = DayInput(tick_target=1, advance=True)
    valid, reason = kernel.validate_day_input(planning_input, expected_tick_target=1)
    assert valid, reason
    _, eod_state = kernel.step(planning_input)
    assert eod_state.phase == "end_of_day"

    eod_input = DayInput(
        tick_target=1,
        advance=True,
        end_of_day=EndOfDayActions(
            upgrade_brains=3,
            sell_washed_dumb=2,
            sell_washed_smart=4,
            convert_workers_dumb=2,
            convert_workers_smart=1,
        ),
    )
    valid, reason = kernel.validate_day_input(eod_input, expected_tick_target=1)
    assert valid, reason
    _, planning_state = kernel.step(eod_input)

    assert planning_state.day_tick == 1
    assert planning_state.phase == "planning"

    convert_cost = int(kernel.loaded_config.config.economy.convert_cost)
    eod_washed_dumb = int(eod_state.inventory.inventories.get("washed_dumb", 0))
    eod_washed_smart = int(eod_state.inventory.inventories.get("washed_smart", 0))
    expected_washed_dumb = eod_washed_dumb - 3 - 2 - (2 * convert_cost)
    expected_washed_smart = eod_washed_smart + 3 - 4 - (1 * convert_cost)
    assert int(planning_state.inventory.inventories.get("washed_dumb", 0)) == expected_washed_dumb
    assert int(planning_state.inventory.inventories.get("washed_smart", 0)) == expected_washed_smart
    assert int(planning_state.worker_pools.dumb_total) == int(eod_state.worker_pools.dumb_total) + 2
    assert int(planning_state.worker_pools.smart_total) == int(eod_state.worker_pools.smart_total) + 1

    sell_dumb_price = int(kernel.loaded_config.config.economy.sell_washed_dumb)
    sell_smart_price = int(kernel.loaded_config.config.economy.sell_washed_smart)
    expected_cash = int(eod_state.inventory.cash) + (2 * sell_dumb_price) + (4 * sell_smart_price)
    assert int(planning_state.inventory.cash) == expected_cash

    eod_kinds = [str(event.get("kind", "")) for event in planning_state.events if str(event.get("kind", "")).startswith("eod_")]
    assert eod_kinds[-5:] == ["eod_opened", "eod_upgrade", "eod_sell", "eod_convert", "eod_confirmed"]
