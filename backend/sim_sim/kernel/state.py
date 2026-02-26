from __future__ import annotations

"""Minimal deterministic sim_sim placeholder kernel for LIVE vertical slice."""

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple


ROOM_IDS: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
UNLOCKED_ROOM_IDS: Tuple[int, ...] = (1, 2, 3, 4, 5)
SUPERVISOR_IDS: Tuple[int, ...] = (1, 2, 3, 4, 5)
PHASES: Tuple[str, ...] = ("planning", "production", "audit", "close")
RESOURCE_KEYS: Tuple[str, ...] = (
    "raw_brains_dumb",
    "raw_brains_smart",
    "washed_dumb",
    "washed_smart",
    "substrate_gallons",
    "ribbon_yards",
)


def supervisor_code(supervisor_id: int) -> str:
    return f"SUP-{int(supervisor_id)}"


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
class RoomState:
    room_id: int
    name: str
    locked: bool
    supervisor: str | None
    workers_assigned_dumb: int
    workers_assigned_smart: int
    workers_present_dumb: int
    workers_present_smart: int
    equipment_condition: float
    stress: float
    discipline: float
    alignment: float
    output_today: Dict[str, int]
    accidents_count: int
    casualties: int


@dataclass(frozen=True)
class SupervisorState:
    code: str
    assigned_room: int | None
    loyalty: float
    confidence: float
    influence: float
    cooldown_days: int


@dataclass(frozen=True)
class InventoryState:
    cash: int
    inventories: Dict[str, int]


@dataclass(frozen=True)
class RegimeState:
    refactor_days: int
    inversion_days: int
    shutdown_except_brewery_today: bool
    weaving_boost_next_day: bool
    global_accident_bonus: float


@dataclass(frozen=True)
class SimSimState:
    day_tick: int
    phase: str
    time_label: str
    assignments: Dict[int, int]
    rooms: Dict[int, RoomState]
    supervisors: Dict[str, SupervisorState]
    inventory: InventoryState
    regime: RegimeState
    security_lead: str
    events: List[dict]
    next_event_id: int


def _initial_assignments(seed: int) -> Dict[int, int]:
    # Deterministic start assignment. Seed only shifts the initial room rotation.
    shift = int(seed) % len(UNLOCKED_ROOM_IDS)
    ordered_rooms = list(UNLOCKED_ROOM_IDS)
    ordered_rooms = ordered_rooms[shift:] + ordered_rooms[:shift]
    return {
        supervisor_id: ordered_rooms[idx]
        for idx, supervisor_id in enumerate(SUPERVISOR_IDS)
    }


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _resource_zeroes() -> Dict[str, int]:
    return {key: 0 for key in RESOURCE_KEYS}


class SimSimKernel:
    """Deterministic day-based kernel placeholder."""

    def __init__(self, seed: int) -> None:
        self._seed = int(seed)
        assignments = _initial_assignments(self._seed)
        regime = RegimeState(
            refactor_days=0,
            inversion_days=0,
            shutdown_except_brewery_today=False,
            weaving_boost_next_day=False,
            global_accident_bonus=0.0,
        )
        supervisors = self._build_supervisors(assignments=assignments, previous=None, day_tick=0)
        rooms = self._build_rooms(
            assignments=assignments,
            supervisors=supervisors,
            previous=None,
            regime=regime,
            day_tick=0,
        )
        inventory = InventoryState(
            cash=1200,
            inventories={
                "raw_brains_dumb": 40,
                "raw_brains_smart": 22,
                "washed_dumb": 18,
                "washed_smart": 10,
                "substrate_gallons": 55,
                "ribbon_yards": 34,
            },
        )
        initial_events: List[dict] = [
            self._make_event(
                tick=0,
                event_id=0,
                kind="bootstrap",
                room_id=1,
                details={"note": "sim_sim live session started"},
            )
        ]
        self._state = SimSimState(
            day_tick=0,
            phase=PHASES[0],
            time_label="06:00",
            assignments=assignments,
            rooms=rooms,
            supervisors=supervisors,
            inventory=inventory,
            regime=regime,
            security_lead=self._pick_security_lead(supervisors),
            events=initial_events,
            next_event_id=1,
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
        next_phase = PHASES[next_tick % len(PHASES)]
        next_time = f"{8 + (next_tick % 10):02d}:00"

        # Deterministic baseline behavior: cycle all supervisors through rooms 1..5.
        assignments = {
            supervisor_id: (((room_id - 1 + 1) % len(UNLOCKED_ROOM_IDS)) + 1)
            for supervisor_id, room_id in sorted(previous.assignments.items())
        }

        # Apply explicit swaps on top of the baseline transition.
        for swap in day_input.supervisor_swaps:
            assignments[int(swap.supervisor_id)] = int(swap.room_id)

        regime = self._build_regime(previous.regime, day_tick=next_tick)
        supervisors = self._build_supervisors(assignments=assignments, previous=previous.supervisors, day_tick=next_tick)
        rooms = self._build_rooms(
            assignments=assignments,
            supervisors=supervisors,
            previous=previous.rooms,
            regime=regime,
            day_tick=next_tick,
        )
        inventory = self._build_inventory(previous.inventory, rooms, regime=regime)
        security_lead = self._pick_security_lead(supervisors)

        new_events, next_event_id = self._build_events(
            previous=previous,
            rooms=rooms,
            inventory=inventory,
            security_lead=security_lead,
            day_tick=next_tick,
        )

        self._state = SimSimState(
            day_tick=next_tick,
            phase=next_phase,
            time_label=next_time,
            assignments=assignments,
            rooms=rooms,
            supervisors=supervisors,
            inventory=inventory,
            regime=regime,
            security_lead=security_lead,
            events=previous.events + new_events,
            next_event_id=next_event_id,
        )
        return previous, self._state

    def _build_regime(self, previous: RegimeState, *, day_tick: int) -> RegimeState:
        refactor_days = max(0, int(previous.refactor_days) - 1)
        inversion_days = max(0, int(previous.inversion_days) - 1)
        if day_tick % 7 == 0:
            refactor_days = 2
        if day_tick % 9 == 0:
            inversion_days = 1
        shutdown_except_brewery_today = day_tick % 10 == 0
        weaving_boost_next_day = day_tick % 4 == 0
        global_accident_bonus = 0.0
        if inversion_days > 0:
            global_accident_bonus += 0.12
        if shutdown_except_brewery_today:
            global_accident_bonus += 0.06
        return RegimeState(
            refactor_days=refactor_days,
            inversion_days=inversion_days,
            shutdown_except_brewery_today=shutdown_except_brewery_today,
            weaving_boost_next_day=weaving_boost_next_day,
            global_accident_bonus=global_accident_bonus,
        )

    def _build_supervisors(
        self,
        *,
        assignments: Mapping[int, int],
        previous: Mapping[str, SupervisorState] | None,
        day_tick: int,
    ) -> Dict[str, SupervisorState]:
        out: Dict[str, SupervisorState] = {}
        for supervisor_id in SUPERVISOR_IDS:
            code = supervisor_code(supervisor_id)
            assigned_room = int(assignments.get(supervisor_id, 1))
            prev = previous.get(code) if previous else None
            if prev is None:
                loyalty = _clamp01(0.52 + 0.03 * ((self._seed + supervisor_id) % 5))
                confidence = _clamp01(0.47 + 0.04 * ((self._seed + 2 * supervisor_id) % 4))
                influence = _clamp01(0.45 + 0.05 * ((self._seed + 3 * supervisor_id) % 4))
                cooldown = 0
            else:
                moved = prev.assigned_room != assigned_room
                loyalty_delta = (((day_tick + supervisor_id) % 3) - 1) * 0.015 - (0.01 if moved else 0.0)
                confidence_delta = (0.012 if not moved else -0.02) + (0.006 if assigned_room == 1 else 0.0)
                influence_target = (prev.influence * 0.6) + ((prev.loyalty + prev.confidence) * 0.2)
                loyalty = _clamp01(prev.loyalty + loyalty_delta)
                confidence = _clamp01(prev.confidence + confidence_delta)
                influence = _clamp01((influence_target * 0.8) + (0.2 * ((loyalty + confidence) * 0.5)))
                cooldown = 2 if moved else max(0, prev.cooldown_days - 1)

            out[code] = SupervisorState(
                code=code,
                assigned_room=assigned_room,
                loyalty=loyalty,
                confidence=confidence,
                influence=influence,
                cooldown_days=cooldown,
            )
        return out

    def _build_rooms(
        self,
        *,
        assignments: Mapping[int, int],
        supervisors: Mapping[str, SupervisorState],
        previous: Mapping[int, RoomState] | None,
        regime: RegimeState,
        day_tick: int,
    ) -> Dict[int, RoomState]:
        supervisor_by_room: Dict[int, str] = {}
        for supervisor_id, room_id in sorted(assignments.items()):
            supervisor_by_room[int(room_id)] = supervisor_code(supervisor_id)

        rooms: Dict[int, RoomState] = {}
        for room_id in ROOM_IDS:
            locked = room_id == 6
            supervisor = None if locked else supervisor_by_room.get(room_id)
            sup = supervisors.get(supervisor) if supervisor else None
            prev = previous.get(room_id) if previous else None

            assigned_dumb = 0 if locked else 4 + ((self._seed + day_tick + room_id) % 4)
            assigned_smart = 0 if locked else 2 + ((self._seed + day_tick + (room_id * 2)) % 3)

            if regime.shutdown_except_brewery_today and room_id != 4:
                assigned_dumb = max(0, assigned_dumb - 2)
                assigned_smart = max(0, assigned_smart - 1)

            present_dumb = max(0, assigned_dumb - ((day_tick + room_id) % 2))
            present_smart = max(0, assigned_smart - ((day_tick + room_id + 1) % 2))

            if prev is None:
                equipment_prev = 0.88 - room_id * 0.03
                stress_prev = 0.28 + ((room_id + day_tick) % 3) * 0.07
            else:
                equipment_prev = prev.equipment_condition
                stress_prev = prev.stress

            equipment_delta = -0.018 - 0.002 * ((day_tick + room_id) % 4)
            if regime.weaving_boost_next_day and room_id == 5:
                equipment_delta += 0.02
            equipment = _clamp01(equipment_prev + equipment_delta)

            stress_delta = (((day_tick + room_id) % 3) - 1) * 0.03 + regime.global_accident_bonus * 0.35
            stress = _clamp01(stress_prev + stress_delta)
            discipline = _clamp01(0.78 - stress * 0.5 + (0.03 if sup and sup.cooldown_days == 0 else -0.02))
            alignment_base = (sup.loyalty + sup.confidence) * 0.5 if sup else 0.4
            alignment = _clamp01(alignment_base - stress * 0.08)

            accidents_count = 0
            casualties = 0
            accident_signal = (self._seed + day_tick + room_id) % 11
            if not locked and (accident_signal == 0 or (equipment < 0.42 and stress > 0.62)):
                accidents_count = 1
                casualties = 1 if ((day_tick + room_id) % 2 == 0) else 0

            output_today = _resource_zeroes()
            if not locked:
                output_today["raw_brains_dumb"] = present_dumb * (2 if room_id in (1, 2) else 1)
                output_today["raw_brains_smart"] = present_smart * (2 if room_id in (2, 3) else 1)
                output_today["washed_dumb"] = present_dumb if room_id in (2, 4) else 0
                output_today["washed_smart"] = present_smart if room_id in (3, 4) else 0
                output_today["substrate_gallons"] = present_dumb + present_smart if room_id in (4, 5) else 0
                output_today["ribbon_yards"] = present_smart * 2 if room_id == 5 else 0

            rooms[room_id] = RoomState(
                room_id=room_id,
                name=f"Room {room_id}",
                locked=locked,
                supervisor=supervisor,
                workers_assigned_dumb=assigned_dumb,
                workers_assigned_smart=assigned_smart,
                workers_present_dumb=present_dumb,
                workers_present_smart=present_smart,
                equipment_condition=equipment,
                stress=stress,
                discipline=discipline,
                alignment=alignment,
                output_today=output_today,
                accidents_count=accidents_count,
                casualties=casualties,
            )
        return rooms

    def _build_inventory(self, previous: InventoryState, rooms: Mapping[int, RoomState], *, regime: RegimeState) -> InventoryState:
        totals = _resource_zeroes()
        casualties = 0
        for room in rooms.values():
            casualties += int(room.casualties)
            for key in RESOURCE_KEYS:
                totals[key] += int(room.output_today.get(key, 0))

        next_inv = dict(previous.inventories)
        next_inv["raw_brains_dumb"] = max(0, int(previous.inventories.get("raw_brains_dumb", 0)) + totals["raw_brains_dumb"])
        next_inv["raw_brains_smart"] = max(0, int(previous.inventories.get("raw_brains_smart", 0)) + totals["raw_brains_smart"])
        next_inv["washed_dumb"] = max(
            0,
            int(previous.inventories.get("washed_dumb", 0)) + totals["washed_dumb"] + (totals["raw_brains_dumb"] // 4),
        )
        next_inv["washed_smart"] = max(
            0,
            int(previous.inventories.get("washed_smart", 0)) + totals["washed_smart"] + (totals["raw_brains_smart"] // 5),
        )
        next_inv["substrate_gallons"] = max(
            0,
            int(previous.inventories.get("substrate_gallons", 0)) + totals["substrate_gallons"] - (totals["washed_dumb"] // 2),
        )
        next_inv["ribbon_yards"] = max(
            0,
            int(previous.inventories.get("ribbon_yards", 0)) + totals["ribbon_yards"] - (totals["washed_smart"] // 4),
        )

        wash_total = next_inv["washed_dumb"] + next_inv["washed_smart"]
        revenue = (wash_total // 2) + (next_inv["ribbon_yards"] // 3)
        penalties = casualties * 35 + (20 if regime.shutdown_except_brewery_today else 0)
        cash = max(0, int(previous.cash) + revenue - penalties)

        return InventoryState(cash=cash, inventories=next_inv)

    def _pick_security_lead(self, supervisors: Mapping[str, SupervisorState]) -> str:
        ordered = sorted(supervisors.values(), key=lambda sup: (-sup.influence, sup.code))
        return ordered[0].code if ordered else supervisor_code(1)

    def _build_events(
        self,
        *,
        previous: SimSimState,
        rooms: Mapping[int, RoomState],
        inventory: InventoryState,
        security_lead: str,
        day_tick: int,
    ) -> tuple[List[dict], int]:
        event_id = int(previous.next_event_id)
        out: List[dict] = []

        out.append(
            self._make_event(
                tick=day_tick,
                event_id=event_id,
                kind="day_advanced",
                details={"day": day_tick, "phase": PHASES[day_tick % len(PHASES)], "security_lead": security_lead},
            )
        )
        event_id += 1

        top_room = max(
            rooms.values(),
            key=lambda room: (
                room.output_today["raw_brains_dumb"]
                + room.output_today["raw_brains_smart"]
                + room.output_today["washed_dumb"]
                + room.output_today["washed_smart"],
                -room.room_id,
            ),
        )
        out.append(
            self._make_event(
                tick=day_tick,
                event_id=event_id,
                kind="room_output",
                room_id=top_room.room_id,
                supervisor=top_room.supervisor,
                details={"output_today": dict(top_room.output_today)},
            )
        )
        event_id += 1

        for room in sorted(rooms.values(), key=lambda r: r.room_id):
            if room.accidents_count <= 0:
                continue
            out.append(
                self._make_event(
                    tick=day_tick,
                    event_id=event_id,
                    kind="accident",
                    room_id=room.room_id,
                    supervisor=room.supervisor,
                    details={"count": room.accidents_count, "casualties": room.casualties},
                )
            )
            event_id += 1

        out.append(
            self._make_event(
                tick=day_tick,
                event_id=event_id,
                kind="ledger_update",
                details={
                    "cash": inventory.cash,
                    "washed_total": inventory.inventories.get("washed_dumb", 0) + inventory.inventories.get("washed_smart", 0),
                },
            )
        )
        event_id += 1

        return out, event_id

    @staticmethod
    def _make_event(
        *,
        tick: int,
        event_id: int,
        kind: str,
        room_id: int | None = None,
        supervisor: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> dict:
        event: Dict[str, object] = {
            "tick": int(tick),
            "event_id": int(event_id),
            "kind": str(kind),
        }
        if room_id is not None:
            event["room_id"] = int(room_id)
        if supervisor is not None:
            event["supervisor"] = str(supervisor)
        if details is not None:
            event["details"] = dict(details)
        return event


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
    lines = [
        f"day_tick={state.day_tick} phase={state.phase} time={state.time_label}",
        f"cash={state.inventory.cash} security_lead={state.security_lead}",
        "supervisor_assignments:",
    ]
    for supervisor_id in SUPERVISOR_IDS:
        room_id = state.assignments.get(supervisor_id, -1)
        code = supervisor_code(supervisor_id)
        sup = state.supervisors.get(code)
        lines.append(
            f"  {code} -> room {room_id} loyalty={sup.loyalty if sup else 0:.2f} "
            f"conf={sup.confidence if sup else 0:.2f} infl={sup.influence if sup else 0:.2f}"
        )
    lines.append("room_metrics:")
    for room_id in ROOM_IDS:
        room = state.rooms.get(room_id)
        if not room:
            continue
        lines.append(
            f"  room {room_id} sup={room.supervisor or '-'} "
            f"equip={room.equipment_condition:.2f} stress={room.stress:.2f} "
            f"disc={room.discipline:.2f} align={room.alignment:.2f} "
            f"casualties={room.casualties}"
        )
    if state.events:
        lines.append("events:")
        for ev in state.events[-4:]:
            lines.append(f"  tick={ev.get('tick')} event_id={ev.get('event_id')} kind={ev.get('kind')} room={ev.get('room_id')}")
    return "\n".join(lines)
