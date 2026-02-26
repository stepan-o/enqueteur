from __future__ import annotations

"""Deterministic sim_sim placeholder kernel (Milestone 1 canon + unlock pacing)."""

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple


ROOM_IDS: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
PHASES: Tuple[str, ...] = ("planning", "production", "audit", "close")
RESOURCE_KEYS: Tuple[str, ...] = (
    "raw_brains_dumb",
    "raw_brains_smart",
    "washed_dumb",
    "washed_smart",
    "substrate_gallons",
    "ribbon_yards",
)

ROOM_NAMES: Dict[int, str] = {
    1: "Security",
    2: "Synaptic Lattice Forge",
    3: "Burn-in Theatre",
    4: "Cognition Substrate Brewery",
    5: "Synapse Weaving Gallery",
    6: "Cortex Assembly Line",
}

# -1 means never unlock (Room 6 is always locked).
ROOM_UNLOCK_DAY: Dict[int, int] = {
    1: 0,
    2: 1,
    3: 2,
    4: 3,
    5: 4,
    6: -1,
}


@dataclass(frozen=True)
class SupervisorProfile:
    numeric_id: int
    code: str
    name: str
    native_room: int
    unlocked_day: int


SUPERVISOR_PROFILES: Tuple[SupervisorProfile, ...] = (
    SupervisorProfile(numeric_id=1, code="L", name="LIMEN", native_room=1, unlocked_day=0),
    SupervisorProfile(numeric_id=2, code="S", name="STILETTO", native_room=2, unlocked_day=1),
    SupervisorProfile(numeric_id=3, code="C", name="CATHEXIS", native_room=3, unlocked_day=2),
    SupervisorProfile(numeric_id=4, code="W", name="RIVET WITCH", native_room=4, unlocked_day=3),
    SupervisorProfile(numeric_id=5, code="T", name="THRUM", native_room=5, unlocked_day=4),
)

SUPERVISOR_CODES: Tuple[str, ...] = tuple(profile.code for profile in SUPERVISOR_PROFILES)
SUPERVISOR_BY_CODE: Dict[str, SupervisorProfile] = {profile.code: profile for profile in SUPERVISOR_PROFILES}
SUPERVISOR_CODE_BY_ID: Dict[int, str] = {profile.numeric_id: profile.code for profile in SUPERVISOR_PROFILES}


def supervisor_code(supervisor_id: int) -> str:
    return SUPERVISOR_CODE_BY_ID.get(int(supervisor_id), f"SUP-{int(supervisor_id)}")


def resolve_supervisor_code(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        token = value.strip().upper()
        if token in SUPERVISOR_BY_CODE:
            return token
        if token.startswith("SUP-") and token[4:].isdigit():
            return SUPERVISOR_CODE_BY_ID.get(int(token[4:]))
        if token.isdigit():
            return SUPERVISOR_CODE_BY_ID.get(int(token))
        return None
    if isinstance(value, int):
        return SUPERVISOR_CODE_BY_ID.get(int(value))
    return None


@dataclass(frozen=True)
class SupervisorSwap:
    supervisor_code: str
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
    unlocked_day: int
    locked: bool
    supervisor: str | None
    workers_assigned_dumb: int | None
    workers_assigned_smart: int | None
    workers_present_dumb: int | None
    workers_present_smart: int | None
    equipment_condition: float | None
    stress: float | None
    discipline: float | None
    alignment: float | None
    output_today: Dict[str, int]
    accidents_count: int
    casualties: int


@dataclass(frozen=True)
class SupervisorState:
    code: str
    name: str
    unlocked_day: int
    native_room: int
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
    assignments: Dict[str, int | None]
    rooms: Dict[int, RoomState]
    supervisors: Dict[str, SupervisorState]
    inventory: InventoryState
    regime: RegimeState
    security_lead: str
    events: List[dict]
    next_event_id: int


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _resource_zeroes() -> Dict[str, int]:
    return {key: 0 for key in RESOURCE_KEYS}


def _is_room_unlocked(room_id: int, day_tick: int) -> bool:
    unlock_day = ROOM_UNLOCK_DAY.get(int(room_id), -1)
    return unlock_day >= 0 and int(day_tick) >= unlock_day


def _unlocked_supervisor_codes(day_tick: int) -> Tuple[str, ...]:
    return tuple(profile.code for profile in SUPERVISOR_PROFILES if int(day_tick) >= profile.unlocked_day)


class SimSimKernel:
    """Deterministic day-based kernel placeholder."""

    def __init__(self, seed: int) -> None:
        self._seed = int(seed)
        assignments = self._initial_assignments(day_tick=0)
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
            cash=900,
            inventories={
                "raw_brains_dumb": 6,
                "raw_brains_smart": 2,
                "washed_dumb": 0,
                "washed_smart": 0,
                "substrate_gallons": 8,
                "ribbon_yards": 6,
            },
        )

        initial_events = [
            self._make_event(
                tick=0,
                event_id=0,
                kind="bootstrap",
                room_id=1,
                supervisor="L",
                details={"note": "sim_sim milestone1 canonical unlock schedule"},
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
            security_lead="L",
            events=initial_events,
            next_event_id=1,
        )

    @property
    def state(self) -> SimSimState:
        return self._state

    @property
    def seed(self) -> int:
        return self._seed

    def _initial_assignments(self, *, day_tick: int) -> Dict[str, int | None]:
        assignments: Dict[str, int | None] = {}
        for code in _unlocked_supervisor_codes(day_tick):
            profile = SUPERVISOR_BY_CODE[code]
            if _is_room_unlocked(profile.native_room, day_tick):
                assignments[code] = int(profile.native_room)
            else:
                assignments[code] = None
        assignments["L"] = 1
        return assignments

    def validate_day_input(self, day_input: DayInput, expected_tick_target: int) -> tuple[bool, str]:
        if day_input.tick_target != expected_tick_target:
            return False, f"tick_target must equal next day tick ({expected_tick_target})"
        if not day_input.advance:
            return False, "advance must be true in this vertical slice"

        unlocked_codes = set(_unlocked_supervisor_codes(expected_tick_target))
        for swap in day_input.supervisor_swaps:
            code = resolve_supervisor_code(swap.supervisor_code)
            if code is None:
                return False, f"unknown supervisor={swap.supervisor_code}"
            if code not in unlocked_codes:
                return False, f"supervisor {code} is not unlocked for day {expected_tick_target}"

            room_id = int(swap.room_id)
            if room_id not in ROOM_IDS:
                return False, f"room_id={room_id} is invalid"
            if room_id == 6:
                return False, "room_id=6 is permanently locked"
            if not _is_room_unlocked(room_id, expected_tick_target):
                return False, f"room_id={room_id} is not unlocked for day {expected_tick_target}"

            # Canon security rule: Room 1 is security and LIMEN-only.
            if room_id == 1 and code != "L":
                return False, "room1 accepts LIMEN only"
            if code == "L" and room_id != 1:
                return False, "LIMEN remains assigned to room1"

        return True, "ok"

    def step(self, day_input: DayInput) -> tuple[SimSimState, SimSimState]:
        """Advance one day tick and return (previous_state, next_state)."""
        previous = self._state
        next_tick = previous.day_tick + 1
        next_phase = PHASES[next_tick % len(PHASES)]
        next_time = f"{8 + (next_tick % 10):02d}:00"

        assignments = self._advance_assignments(previous.assignments, day_tick=next_tick, day_input=day_input)
        regime = self._build_regime(previous.regime, day_tick=next_tick)
        supervisors = self._build_supervisors(assignments=assignments, previous=previous.supervisors, day_tick=next_tick)
        rooms = self._build_rooms(
            assignments=assignments,
            supervisors=supervisors,
            previous=previous.rooms,
            regime=regime,
            day_tick=next_tick,
        )
        inventory = self._build_inventory(previous.inventory, rooms=rooms, regime=regime)
        security_lead = "L" if "L" in supervisors else self._pick_security_lead(supervisors)

        new_events, next_event_id = self._build_events(
            previous=previous,
            rooms=rooms,
            supervisors=supervisors,
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

    def _advance_assignments(
        self,
        previous_assignments: Mapping[str, int | None],
        *,
        day_tick: int,
        day_input: DayInput,
    ) -> Dict[str, int | None]:
        unlocked_codes = _unlocked_supervisor_codes(day_tick)
        assignments: Dict[str, int | None] = {}

        for code in unlocked_codes:
            profile = SUPERVISOR_BY_CODE[code]
            if code == "L":
                assignments[code] = 1
                continue

            prev_room = previous_assignments.get(code)
            if isinstance(prev_room, int) and prev_room in ROOM_IDS and _is_room_unlocked(prev_room, day_tick) and prev_room != 6:
                assignments[code] = int(prev_room)
            elif _is_room_unlocked(profile.native_room, day_tick):
                assignments[code] = int(profile.native_room)
            else:
                assignments[code] = None

        for swap in day_input.supervisor_swaps:
            code = resolve_supervisor_code(swap.supervisor_code)
            if code is None or code not in assignments:
                continue
            assignments[code] = int(swap.room_id)

        # Canon hard rule: LIMEN is always security lead in room1.
        assignments["L"] = 1

        # One supervisor per room (deterministic resolution by supervisor code order).
        occupied: Dict[int, str] = {}
        for code in sorted(assignments.keys()):
            room = assignments.get(code)
            if room is None:
                continue
            if room in occupied:
                assignments[code] = None
            else:
                occupied[room] = code

        return assignments

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
            global_accident_bonus += 0.10
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
        assignments: Mapping[str, int | None],
        previous: Mapping[str, SupervisorState] | None,
        day_tick: int,
    ) -> Dict[str, SupervisorState]:
        out: Dict[str, SupervisorState] = {}
        for code in _unlocked_supervisor_codes(day_tick):
            profile = SUPERVISOR_BY_CODE[code]
            assigned_room = assignments.get(code)
            prev = previous.get(code) if previous else None

            if prev is None:
                # Deterministic profile initialization.
                loyalty = _clamp01(0.55 + 0.04 * ((self._seed + profile.numeric_id) % 4))
                confidence = _clamp01(0.50 + 0.03 * ((self._seed + profile.numeric_id * 2) % 5))
                influence = _clamp01(0.46 + 0.04 * ((self._seed + profile.numeric_id * 3) % 5))
                cooldown = 0
            else:
                moved = prev.assigned_room != assigned_room
                loyalty = _clamp01(prev.loyalty + (((day_tick + profile.numeric_id) % 3) - 1) * 0.012)
                confidence = _clamp01(prev.confidence + (0.01 if not moved else -0.015))
                influence = _clamp01(prev.influence * 0.7 + ((loyalty + confidence) * 0.15))
                cooldown = 2 if moved else max(0, prev.cooldown_days - 1)

            out[code] = SupervisorState(
                code=code,
                name=profile.name,
                unlocked_day=profile.unlocked_day,
                native_room=profile.native_room,
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
        assignments: Mapping[str, int | None],
        supervisors: Mapping[str, SupervisorState],
        previous: Mapping[int, RoomState] | None,
        regime: RegimeState,
        day_tick: int,
    ) -> Dict[int, RoomState]:
        supervisor_by_room: Dict[int, str] = {}
        for code in sorted(assignments.keys()):
            room_id = assignments.get(code)
            if isinstance(room_id, int):
                supervisor_by_room[room_id] = code

        rooms: Dict[int, RoomState] = {}
        for room_id in ROOM_IDS:
            unlock_day = ROOM_UNLOCK_DAY[room_id]
            room_unlocked = _is_room_unlocked(room_id, day_tick)
            locked = (room_id == 6) or (not room_unlocked)

            # Room1 hard rule: security lead only, no workers/production/accidents/decay.
            if room_id == 1:
                rooms[room_id] = RoomState(
                    room_id=room_id,
                    name=ROOM_NAMES[room_id],
                    unlocked_day=unlock_day,
                    locked=False,
                    supervisor="L" if "L" in supervisors else None,
                    workers_assigned_dumb=None,
                    workers_assigned_smart=None,
                    workers_present_dumb=None,
                    workers_present_smart=None,
                    equipment_condition=1.0,
                    stress=None,
                    discipline=None,
                    alignment=None,
                    output_today=_resource_zeroes(),
                    accidents_count=0,
                    casualties=0,
                )
                continue

            # Room6 hard rule: always locked/inactive.
            if room_id == 6:
                rooms[room_id] = RoomState(
                    room_id=room_id,
                    name=ROOM_NAMES[room_id],
                    unlocked_day=unlock_day,
                    locked=True,
                    supervisor=None,
                    workers_assigned_dumb=None,
                    workers_assigned_smart=None,
                    workers_present_dumb=None,
                    workers_present_smart=None,
                    equipment_condition=None,
                    stress=None,
                    discipline=None,
                    alignment=None,
                    output_today=_resource_zeroes(),
                    accidents_count=0,
                    casualties=0,
                )
                continue

            # Not-yet-unlocked rooms (2..5 before unlock): locked and inactive.
            if locked:
                rooms[room_id] = RoomState(
                    room_id=room_id,
                    name=ROOM_NAMES[room_id],
                    unlocked_day=unlock_day,
                    locked=True,
                    supervisor=None,
                    workers_assigned_dumb=None,
                    workers_assigned_smart=None,
                    workers_present_dumb=None,
                    workers_present_smart=None,
                    equipment_condition=None,
                    stress=None,
                    discipline=None,
                    alignment=None,
                    output_today=_resource_zeroes(),
                    accidents_count=0,
                    casualties=0,
                )
                continue

            supervisor = supervisor_by_room.get(room_id)
            sup = supervisors.get(supervisor) if supervisor else None
            prev = previous.get(room_id) if previous else None

            assigned_dumb = 3 + ((self._seed + day_tick + room_id) % 3)
            assigned_smart = 1 + ((self._seed + day_tick + room_id * 2) % 2)
            if sup is None:
                assigned_dumb = max(0, assigned_dumb - 2)
                assigned_smart = max(0, assigned_smart - 1)

            if regime.shutdown_except_brewery_today and room_id != 4:
                assigned_dumb = max(0, assigned_dumb - 2)
                assigned_smart = max(0, assigned_smart - 1)

            present_dumb = max(0, assigned_dumb - ((day_tick + room_id) % 2))
            present_smart = max(0, assigned_smart - ((day_tick + room_id + 1) % 2))

            if prev is None or prev.equipment_condition is None:
                equipment_prev = 0.84 - (room_id - 2) * 0.04
                stress_prev = 0.26 + ((room_id + day_tick) % 3) * 0.05
            else:
                equipment_prev = prev.equipment_condition
                stress_prev = prev.stress if prev.stress is not None else 0.35

            equipment_delta = -0.014 - 0.002 * ((day_tick + room_id) % 4)
            if regime.weaving_boost_next_day and room_id == 5:
                equipment_delta += 0.012
            equipment = _clamp01(equipment_prev + equipment_delta)

            stress_delta = (((day_tick + room_id) % 3) - 1) * 0.028 + regime.global_accident_bonus * 0.30
            stress = _clamp01(stress_prev + stress_delta)
            discipline = _clamp01(0.79 - stress * 0.48 + (0.03 if sup and sup.cooldown_days == 0 else -0.03))
            alignment_base = (sup.loyalty + sup.confidence) * 0.5 if sup else 0.45
            alignment = _clamp01(alignment_base - stress * 0.10)

            accidents_count = 0
            casualties = 0
            accident_signal = (self._seed + day_tick + room_id) % 11
            if accident_signal == 0 or (equipment < 0.38 and stress > 0.63):
                accidents_count = 1
                casualties = 1 if ((day_tick + room_id) % 2 == 0) else 0

            output_today = _resource_zeroes()
            output_today["raw_brains_dumb"] = present_dumb * (2 if room_id == 2 else 1)
            output_today["raw_brains_smart"] = present_smart * (2 if room_id in (2, 3) else 1)
            output_today["washed_dumb"] = present_dumb if room_id in (2, 4) else 0
            output_today["washed_smart"] = present_smart if room_id in (3, 4) else 0
            output_today["substrate_gallons"] = present_dumb + present_smart if room_id in (4, 5) else 0
            output_today["ribbon_yards"] = present_smart * 2 if room_id == 5 else 0

            rooms[room_id] = RoomState(
                room_id=room_id,
                name=ROOM_NAMES[room_id],
                unlocked_day=unlock_day,
                locked=False,
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

    def _build_inventory(self, previous: InventoryState, *, rooms: Mapping[int, RoomState], regime: RegimeState) -> InventoryState:
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
            int(previous.inventories.get("washed_dumb", 0)) + totals["washed_dumb"] + (totals["raw_brains_dumb"] // 5),
        )
        next_inv["washed_smart"] = max(
            0,
            int(previous.inventories.get("washed_smart", 0)) + totals["washed_smart"] + (totals["raw_brains_smart"] // 6),
        )
        next_inv["substrate_gallons"] = max(
            0,
            int(previous.inventories.get("substrate_gallons", 0)) + totals["substrate_gallons"] - (totals["washed_dumb"] // 3),
        )
        next_inv["ribbon_yards"] = max(
            0,
            int(previous.inventories.get("ribbon_yards", 0)) + totals["ribbon_yards"] - (totals["washed_smart"] // 5),
        )

        wash_total = next_inv["washed_dumb"] + next_inv["washed_smart"]
        revenue = (wash_total // 3) + (next_inv["ribbon_yards"] // 4)
        penalties = casualties * 30 + (18 if regime.shutdown_except_brewery_today else 0)
        cash = max(0, int(previous.cash) + revenue - penalties)

        return InventoryState(cash=cash, inventories=next_inv)

    def _pick_security_lead(self, supervisors: Mapping[str, SupervisorState]) -> str:
        if "L" in supervisors:
            return "L"
        ordered = sorted(supervisors.values(), key=lambda sup: (-sup.influence, sup.code))
        return ordered[0].code if ordered else "L"

    def _build_events(
        self,
        *,
        previous: SimSimState,
        rooms: Mapping[int, RoomState],
        supervisors: Mapping[str, SupervisorState],
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

        for room_id in ROOM_IDS:
            prev_room = previous.rooms.get(room_id)
            now_room = rooms.get(room_id)
            if not prev_room or not now_room:
                continue
            if prev_room.locked and not now_room.locked:
                out.append(
                    self._make_event(
                        tick=day_tick,
                        event_id=event_id,
                        kind="room_unlocked",
                        room_id=room_id,
                        details={"name": now_room.name, "unlocked_day": now_room.unlocked_day},
                    )
                )
                event_id += 1

        for code in SUPERVISOR_CODES:
            if code in supervisors and code not in previous.supervisors:
                sup = supervisors[code]
                out.append(
                    self._make_event(
                        tick=day_tick,
                        event_id=event_id,
                        kind="supervisor_unlocked",
                        supervisor=sup.code,
                        room_id=sup.assigned_room,
                        details={"name": sup.name, "native_room": sup.native_room, "unlocked_day": sup.unlocked_day},
                    )
                )
                event_id += 1

        active_rooms = [room for room in rooms.values() if room.room_id in (2, 3, 4, 5) and not room.locked]
        if active_rooms:
            top_room = max(
                active_rooms,
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

        for room in sorted(active_rooms, key=lambda r: r.room_id):
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
    """Parse CLI swap tokens: 'L:2,S:3' or legacy numeric '2:2,3:3'."""
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
            raise ValueError(f"invalid swap token '{pair}', expected 'supervisor:room_id'")
        sup_raw, room_raw = pair.split(":", 1)
        code = resolve_supervisor_code(sup_raw)
        if code is None:
            raise ValueError(f"unknown supervisor '{sup_raw}'")
        swaps.append(SupervisorSwap(supervisor_code=code, room_id=int(room_raw)))
    return tuple(swaps)


def format_state_for_cli(state: SimSimState) -> str:
    lines = [
        f"day_tick={state.day_tick} phase={state.phase} time={state.time_label}",
        f"cash={state.inventory.cash} security_lead={state.security_lead}",
        "supervisors:",
    ]

    for code in SUPERVISOR_CODES:
        sup = state.supervisors.get(code)
        if not sup:
            continue
        lines.append(
            f"  {sup.code} ({sup.name}) -> room {sup.assigned_room if sup.assigned_room is not None else '-'} "
            f"L={sup.loyalty:.2f} C={sup.confidence:.2f} I={sup.influence:.2f} cooldown={sup.cooldown_days}"
        )

    lines.append("rooms:")
    for room_id in ROOM_IDS:
        room = state.rooms.get(room_id)
        if not room:
            continue
        if room.locked:
            lines.append(f"  room {room.room_id} {room.name}: LOCKED (unlock_day={room.unlocked_day})")
            continue
        if room.room_id == 1:
            lines.append(f"  room1 Security: lead={room.supervisor or '-'} (no workers/output)")
            continue
        lines.append(
            f"  room {room.room_id} {room.name}: sup={room.supervisor or '-'} "
            f"workers={room.workers_present_dumb}/{room.workers_present_smart} "
            f"equip={room.equipment_condition:.2f} stress={room.stress:.2f} casualties={room.casualties}"
        )

    if state.events:
        lines.append("events:")
        for ev in state.events[-6:]:
            lines.append(
                f"  tick={ev.get('tick')} event_id={ev.get('event_id')} "
                f"kind={ev.get('kind')} room={ev.get('room_id')} supervisor={ev.get('supervisor')}"
            )

    return "\n".join(lines)
