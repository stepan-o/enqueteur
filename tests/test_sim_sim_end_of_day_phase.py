from __future__ import annotations

import copy
import json

from backend.sim_sim.kernel.state import DayInput, PromptResponse, SimSimKernel


def _write_config(tmp_path, raw: dict, name: str) -> str:
    config_path = tmp_path / name
    config_path.write_text(json.dumps(raw), encoding="utf-8")
    return str(config_path)


def _kernel_without_prompts(tmp_path) -> SimSimKernel:
    base = SimSimKernel(seed=7)
    config_raw = copy.deepcopy(base.loaded_config.raw)
    config_raw["conflicts"]["hostile_pairs"] = []
    config_raw["guardrails"]["prevent_critical_before_day"] = 999
    config_path = _write_config(tmp_path, config_raw, "end_of_day_phase_config.json")
    return SimSimKernel(seed=7, config_path=config_path)


def _kernel_with_forced_prompt(tmp_path) -> SimSimKernel:
    base = SimSimKernel(seed=5)
    config_raw = copy.deepcopy(base.loaded_config.raw)
    config_raw["conflicts"]["hostile_pairs"] = []
    config_raw["guardrails"]["prevent_critical_before_day"] = 0
    config_raw["confidence"]["threshold_critical"] = 0.0
    config_path = _write_config(tmp_path, config_raw, "forced_prompt_config.json")
    return SimSimKernel(seed=5, config_path=config_path)


def test_planning_without_prompts_enters_end_of_day_phase(tmp_path) -> None:
    kernel = _kernel_without_prompts(tmp_path)
    planning_input = DayInput(tick_target=1, advance=True)

    valid, reason = kernel.validate_day_input(planning_input, expected_tick_target=1)
    assert valid, reason

    previous, current = kernel.step(planning_input)

    assert previous.day_tick == 0
    assert current.day_tick == 0
    assert current.phase == "end_of_day"
    assert not kernel.unresolved_prompts
    # The resolved day is preserved for UI/EOD display.
    assert current.rooms[2].locked is False
    assert any(int(event.get("tick", -1)) == 1 for event in current.events)


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
