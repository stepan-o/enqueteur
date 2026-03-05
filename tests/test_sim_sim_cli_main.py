from __future__ import annotations

from dataclasses import replace

from backend.sim_sim.app.main import _build_choose_day_input
from backend.sim_sim.kernel.state import PromptState, SimSimKernel


def _prompt(prompt_id: str, *, choices: tuple[str, ...], kind: str = "conflict") -> PromptState:
    return PromptState(
        prompt_id=prompt_id,
        kind=kind,
        tick=1,
        choices=choices,
        status="pending",
        selected_choice=None,
        payload={},
    )


def test_choose_with_prompt_id_and_choice_builds_prompt_response_input() -> None:
    kernel = SimSimKernel(seed=7)
    state = replace(
        kernel.state,
        phase="awaiting_prompts",
        prompts=[_prompt("prompt_conflict_1_2_3", choices=("support_A", "support_B"))],
    )

    day_input, error = _build_choose_day_input(
        ["choose", "prompt_conflict_1_2_3", "support_B"],
        state=state,
        tick_target=2,
    )

    assert error is None
    assert day_input is not None
    assert day_input.tick_target == 2
    assert len(day_input.prompt_responses) == 1
    assert day_input.prompt_responses[0].prompt_id == "prompt_conflict_1_2_3"
    assert day_input.prompt_responses[0].choice == "support_B"


def test_choose_shorthand_maps_a_b_when_single_prompt() -> None:
    kernel = SimSimKernel(seed=7)
    state = replace(
        kernel.state,
        phase="awaiting_prompts",
        prompts=[_prompt("prompt_conflict_2_2_3", choices=("support_A", "support_B"))],
    )

    day_input, error = _build_choose_day_input(
        ["choose", "A"],
        state=state,
        tick_target=3,
    )

    assert error is None
    assert day_input is not None
    assert len(day_input.prompt_responses) == 1
    assert day_input.prompt_responses[0].prompt_id == "prompt_conflict_2_2_3"
    assert day_input.prompt_responses[0].choice == "support_A"


def test_choose_shorthand_requires_single_prompt() -> None:
    kernel = SimSimKernel(seed=7)
    state = replace(
        kernel.state,
        phase="awaiting_prompts",
        prompts=[
            _prompt("prompt_conflict_2_2_3", choices=("support_A", "support_B")),
            _prompt("prompt_critical_2_L", choices=("allow", "suppress"), kind="critical"),
        ],
    )

    day_input, error = _build_choose_day_input(
        ["choose", "A"],
        state=state,
        tick_target=3,
    )

    assert day_input is None
    assert error is not None
    assert "exactly one unresolved prompt" in error


def test_choose_invalid_choice_returns_error() -> None:
    kernel = SimSimKernel(seed=7)
    state = replace(
        kernel.state,
        phase="awaiting_prompts",
        prompts=[_prompt("prompt_critical_3_T", choices=("allow", "suppress"), kind="critical")],
    )

    day_input, error = _build_choose_day_input(
        ["choose", "A"],
        state=state,
        tick_target=4,
    )

    assert day_input is None
    assert error is not None
    assert "invalid choice" in error
