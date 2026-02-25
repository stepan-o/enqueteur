from __future__ import annotations

"""Minimal deterministic sim_sim placeholder kernel for LIVE vertical slice."""

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


ROOM_IDS: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
UNLOCKED_ROOM_IDS: Tuple[int, ...] = (1, 2, 3, 4, 5)
SUPERVISOR_IDS: Tuple[int, ...] = (1, 2, 3, 4, 5)


@dataclass(frozen=True)
class SupervisorSwap:
    supervisor_id: int
    room_id: int


@dataclass(frozen=True)
class DayInput:
    tick_target: int
    advance: bool = True
    supervisor_swaps: Tuple[SupervisorSwap, ...] = ()


@dataclass(frozen=True)
class SimSimState:
    day_tick: int
    assignments: Dict[int, int]
    events: List[dict]


def _initial_assignments(seed: int) -> Dict[int, int]:
    # Deterministic start assignment. Seed only shifts the initial room rotation.
    shift = int(seed) % len(UNLOCKED_ROOM_IDS)
    ordered_rooms = list(UNLOCKED_ROOM_IDS)
    ordered_rooms = ordered_rooms[shift:] + ordered_rooms[:shift]
    return {
        supervisor_id: ordered_rooms[idx]
        for idx, supervisor_id in enumerate(SUPERVISOR_IDS)
    }


class SimSimKernel:
    """Deterministic day-based kernel placeholder."""

    def __init__(self, seed: int) -> None:
        self._seed = int(seed)
        self._state = SimSimState(
            day_tick=0,
            assignments=_initial_assignments(self._seed),
            events=[self._make_event(tick=0, event_id=0, room_id=1, kind="bootstrap")],
        )

    @property
    def state(self) -> SimSimState:
        return self._state

    @property
    def seed(self) -> int:
        return self._seed

    def validate_day_input(self, day_input: DayInput, expected_tick_target: int) -> tuple[bool, str]:
        if day_input.tick_target != expected_tick_target:
            return False, f"tick_target must equal next day tick ({expected_tick_target})"
        if not day_input.advance:
            return False, "advance must be true in this vertical slice"
        for swap in day_input.supervisor_swaps:
            if swap.supervisor_id not in SUPERVISOR_IDS:
                return False, f"unknown supervisor_id={swap.supervisor_id}"
            if swap.room_id not in UNLOCKED_ROOM_IDS:
                return False, f"room_id={swap.room_id} is invalid or locked"
        return True, "ok"

    def step(self, day_input: DayInput) -> tuple[SimSimState, SimSimState]:
        """Advance one day tick and return (previous_state, next_state)."""
        previous = self._state
        next_tick = previous.day_tick + 1

        # Deterministic baseline behavior: cycle all supervisors through rooms 1..5.
        assignments = {
            supervisor_id: (((room_id - 1 + 1) % len(UNLOCKED_ROOM_IDS)) + 1)
            for supervisor_id, room_id in sorted(previous.assignments.items())
        }

        # Apply explicit swaps on top of the baseline transition.
        for swap in day_input.supervisor_swaps:
            assignments[int(swap.supervisor_id)] = int(swap.room_id)

        focus_supervisor = ((next_tick - 1) % len(SUPERVISOR_IDS)) + 1
        focus_room = assignments[focus_supervisor]
        events = [self._make_event(tick=next_tick, event_id=0, room_id=focus_room, kind="day_advanced")]

        self._state = SimSimState(day_tick=next_tick, assignments=assignments, events=events)
        return previous, self._state

    @staticmethod
    def _make_event(*, tick: int, event_id: int, room_id: int, kind: str) -> dict:
        return {
            "tick": int(tick),
            "event_id": int(event_id),
            "origin": "sim_sim",
            "payload": {
                "kind": str(kind),
                "room_id": int(room_id),
            },
        }


def parse_swaps(tokens: Sequence[str]) -> Tuple[SupervisorSwap, ...]:
    """Parse simple CLI swap tokens: 'sup:room,sup:room'."""
    if not tokens:
        return ()
    raw = " ".join(tokens).strip()
    if not raw:
        return ()
    swaps: List[SupervisorSwap] = []
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if ":" not in pair:
            raise ValueError(f"invalid swap token '{pair}', expected 'supervisor_id:room_id'")
        sup_raw, room_raw = pair.split(":", 1)
        swaps.append(SupervisorSwap(supervisor_id=int(sup_raw), room_id=int(room_raw)))
    return tuple(swaps)


def format_state_for_cli(state: SimSimState) -> str:
    lines = [f"day_tick={state.day_tick}", "supervisor_assignments:"]
    for supervisor_id in SUPERVISOR_IDS:
        room_id = state.assignments.get(supervisor_id, -1)
        lines.append(f"  supervisor {supervisor_id} -> room {room_id}")
    if state.events:
        lines.append("events:")
        for ev in state.events:
            lines.append(
                f"  tick={ev.get('tick')} event_id={ev.get('event_id')} kind={ev.get('payload', {}).get('kind')} room={ev.get('payload', {}).get('room_id')}"
            )
    return "\n".join(lines)

