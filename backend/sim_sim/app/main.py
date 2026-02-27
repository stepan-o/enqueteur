from __future__ import annotations

"""sim_sim LIVE entrypoint."""

import argparse
import asyncio
import logging
from typing import Sequence

from backend.sim_sim.kernel.state import DayInput, PromptResponse, PromptState, SimSimState, parse_swaps
from backend.sim_sim.live.session_host import SessionHost
from backend.sim_sim.live.ws_server import SimSimWsServer


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="sim_sim live interactive day runner")
    parser.add_argument("--mode", type=str, default="interactive", choices=("interactive",))
    parser.add_argument("--live", action="store_true", help="Enable LIVE websocket server on ws://localhost:7777/kvp")
    parser.add_argument("--seed", type=int, default=7, help="Deterministic seed for sim_sim kernel")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Optional path to sim_sim config YAML/JSON (defaults to sim_sim_1.default.yaml)",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    return parser


async def _readline(prompt: str) -> str:
    return await asyncio.to_thread(input, prompt)


def _print_help() -> None:
    print("commands:")
    print("  <enter> | next                advance one day")
    print("  next 1:2,3:4                  advance and swap supervisor assignments")
    print("  choose <prompt_id> <choice>   resolve one pending prompt while awaiting prompts")
    print("  choose A|B                    shorthand when exactly one pending prompt supports A/B mapping")
    print("  show                          print current state")
    print("  help                          show this help")
    print("  quit | exit                   stop")


def _unresolved_prompts(state: SimSimState) -> list[PromptState]:
    return [prompt for prompt in state.prompts if prompt.status != "resolved"]


def _choice_aliases(prompt: PromptState) -> dict[str, str]:
    alias_candidates: dict[str, set[str]] = {}
    for choice in prompt.choices:
        text = str(choice).strip()
        if not text:
            continue
        key = text.lower()
        alias_candidates.setdefault(key, set()).add(text)
        if key.endswith("_a"):
            alias_candidates.setdefault("a", set()).add(text)
        if key.endswith("_b"):
            alias_candidates.setdefault("b", set()).add(text)

    aliases: dict[str, str] = {}
    for alias, values in alias_candidates.items():
        if len(values) == 1:
            aliases[alias] = next(iter(values))
    return aliases


def _resolve_prompt_choice(prompt: PromptState, token: str) -> str | None:
    aliases = _choice_aliases(prompt)
    return aliases.get(token.strip().lower())


def _print_pending_prompts(state: SimSimState) -> None:
    pending = _unresolved_prompts(state)
    if not pending:
        print("no pending prompts")
        return
    print("pending prompts:")
    for prompt in pending:
        choices = ", ".join(str(choice) for choice in prompt.choices)
        print(
            f"  - {prompt.prompt_id} kind={prompt.kind} tick={prompt.tick} "
            f"choices=[{choices}]"
        )


def _build_choose_day_input(
    tokens: Sequence[str],
    *,
    state: SimSimState,
    tick_target: int,
) -> tuple[DayInput | None, str | None]:
    pending = _unresolved_prompts(state)
    if not pending:
        return None, "no unresolved prompts; use 'next' instead"

    if len(tokens) < 2:
        return None, "usage: choose <prompt_id> <choice> (or choose A|B for a single prompt)"

    if len(tokens) == 2:
        if len(pending) != 1:
            return None, "choose A/B shorthand requires exactly one unresolved prompt"
        prompt = pending[0]
        resolved_choice = _resolve_prompt_choice(prompt, tokens[1])
        if resolved_choice is None:
            return None, f"invalid choice '{tokens[1]}' for {prompt.prompt_id}"
        return (
            DayInput(
                tick_target=tick_target,
                advance=True,
                prompt_responses=(PromptResponse(prompt_id=prompt.prompt_id, choice=resolved_choice),),
            ),
            None,
        )

    prompt_id = str(tokens[1]).strip()
    choice_token = " ".join(tokens[2:]).strip()
    prompt = next((item for item in pending if item.prompt_id == prompt_id), None)
    if prompt is None:
        ids = ", ".join(item.prompt_id for item in pending)
        return None, f"unknown prompt_id '{prompt_id}'. pending: {ids}"
    resolved_choice = _resolve_prompt_choice(prompt, choice_token)
    if resolved_choice is None:
        choices = ", ".join(str(choice) for choice in prompt.choices)
        return None, f"invalid choice '{choice_token}' for {prompt_id}; valid: {choices}"

    return (
        DayInput(
            tick_target=tick_target,
            advance=True,
            prompt_responses=(PromptResponse(prompt_id=prompt.prompt_id, choice=resolved_choice),),
        ),
        None,
    )


async def _interactive_loop(session_host: SessionHost) -> None:
    print("sim_sim interactive mode")
    _print_help()
    print(session_host.describe_state())
    while True:
        raw = (await _readline("sim_sim> ")).strip()
        if raw in ("quit", "exit"):
            return
        if raw in ("help", "?"):
            _print_help()
            continue
        if raw == "show":
            print(session_host.describe_state())
            continue

        tokens = raw.split()
        command = tokens[0] if tokens else "next"
        if command not in ("next", "choose"):
            print("unknown command; use 'help'")
            continue

        next_tick = session_host.current_tick + 1
        current_state = session_host.current_state
        fallback_input: DayInput

        if command == "next":
            if current_state.phase == "awaiting_prompts":
                print("cannot advance: unresolved prompts require responses first")
                _print_pending_prompts(current_state)
                print("use: choose <prompt_id> <choice>")
                continue
            try:
                swaps = parse_swaps(tokens[1:])
            except ValueError as exc:
                print(f"invalid swap format: {exc}")
                continue
            fallback_input = DayInput(
                tick_target=next_tick,
                advance=True,
                supervisor_swaps=swaps,
            )
        else:
            if current_state.phase != "awaiting_prompts":
                print("choose is only available while phase=awaiting_prompts")
                continue
            _print_pending_prompts(current_state)
            choose_input, choose_error = _build_choose_day_input(tokens, state=current_state, tick_target=next_tick)
            if choose_input is None:
                print(choose_error or "invalid choose command")
                continue
            fallback_input = choose_input

        accepted, reason = await session_host.submit_day_input(fallback_input, source="cli")
        if not accepted and "already queued" not in reason:
            print(f"input rejected: {reason}")
            continue

        to_tick, used_input = await session_host.advance_day(fallback_input)
        if not accepted and "already queued" in reason:
            print(f"used queued input for tick {to_tick}")
        elif command == "choose":
            print(f"resolved prompts and advanced to tick {to_tick}")
        elif used_input.supervisor_swaps:
            print(f"applied swaps for tick {to_tick}")
        else:
            print(f"advanced to tick {to_tick}")
        print(session_host.describe_state())


async def _run(args: argparse.Namespace) -> None:
    session_host = SessionHost(seed=int(args.seed), config_path=args.config)
    ws_server: SimSimWsServer | None = None
    if bool(args.live):
        ws_server = SimSimWsServer(
            session_host=session_host,
            host=str(args.host),
            port=int(args.port),
            route_path="/kvp",
        )
        await ws_server.start()

    try:
        await _interactive_loop(session_host)
    finally:
        if ws_server is not None:
            await ws_server.stop()


def main(argv: Sequence[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = _build_parser()
    args = parser.parse_args(argv)
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
