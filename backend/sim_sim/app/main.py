from __future__ import annotations

"""sim_sim LIVE entrypoint."""

import argparse
import asyncio
import logging
from typing import Sequence

from backend.sim_sim.kernel.state import DayInput, parse_swaps
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
    print("  show                          print current state")
    print("  help                          show this help")
    print("  quit | exit                   stop")


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
        if command != "next":
            print("unknown command; use 'help'")
            continue

        try:
            swaps = parse_swaps(tokens[1:])
        except ValueError as exc:
            print(f"invalid swap format: {exc}")
            continue

        next_tick = session_host.current_tick + 1
        fallback_input = DayInput(
            tick_target=next_tick,
            advance=True,
            supervisor_swaps=swaps,
        )
        accepted, reason = await session_host.submit_day_input(fallback_input, source="cli")
        if not accepted and "already queued" not in reason:
            print(f"input rejected: {reason}")
            continue

        to_tick, used_input = await session_host.advance_day(fallback_input)
        if not accepted and "already queued" in reason:
            print(f"used queued input for tick {to_tick}")
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
