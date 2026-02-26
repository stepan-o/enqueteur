from __future__ import annotations

"""sim_sim kernel: config-driven deterministic day pipeline (Spec v1)."""

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Tuple

from backend.sim_sim.config import LoadedSimSimConfig, load_sim_sim_config


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
ROOM_CODES: Dict[int, str] = {
    1: "security",
    2: "conveyor",
    3: "theatre",
    4: "brewery",
    5: "weaving",
    6: "cortex",
}

ROOM_NEIGHBORS: Dict[int, Tuple[int, ...]] = {
    1: (2, 4),
    2: (1, 3, 5),
    3: (2, 6),
    4: (1, 5),
    5: (2, 4, 6),
    6: (3, 5),
}


@dataclass(frozen=True)
class SupervisorProfile:
    numeric_id: int
    code: str
    name: str
    native_room: int


SUPERVISOR_PROFILES: Tuple[SupervisorProfile, ...] = (
    SupervisorProfile(numeric_id=1, code="L", name="LIMEN", native_room=1),
    SupervisorProfile(numeric_id=2, code="S", name="STILETTO", native_room=2),
    SupervisorProfile(numeric_id=3, code="C", name="CATHEXIS", native_room=3),
    SupervisorProfile(numeric_id=4, code="W", name="RIVET WITCH", native_room=4),
    SupervisorProfile(numeric_id=5, code="T", name="THRUM", native_room=5),
)

SUPERVISOR_CODES: Tuple[str, ...] = tuple(profile.code for profile in SUPERVISOR_PROFILES)
SUPERVISOR_BY_CODE: Dict[str, SupervisorProfile] = {profile.code: profile for profile in SUPERVISOR_PROFILES}
SUPERVISOR_CODE_BY_ID: Dict[int, str] = {profile.numeric_id: profile.code for profile in SUPERVISOR_PROFILES}


@dataclass(frozen=True)
class SupervisorSwap:
    supervisor_code: str
    room_id: int


@dataclass(frozen=True)
class WorkerAssignment:
    dumb: int
    smart: int


@dataclass(frozen=True)
class EndOfDayActions:
    sell_washed_dumb: int = 0
    sell_washed_smart: int = 0
    convert_workers_dumb: int = 0
    convert_workers_smart: int = 0
    upgrade_brains: int = 0


@dataclass(frozen=True)
class PromptResponse:
    prompt_id: str
    choice: str


@dataclass(frozen=True)
class DayInput:
    tick_target: int
    advance: bool = True
    supervisor_swaps: Tuple[SupervisorSwap, ...] = ()
    set_supervisors: Mapping[int, str | None] = field(default_factory=dict)
    set_workers: Mapping[int, WorkerAssignment] = field(default_factory=dict)
    end_of_day: EndOfDayActions = field(default_factory=EndOfDayActions)
    prompt_responses: Tuple[PromptResponse, ...] = ()


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
class WorkerPoolState:
    dumb_total: int
    smart_total: int


@dataclass(frozen=True)
class RegimeState:
    refactor_days: int
    inversion_days: int
    shutdown_except_brewery_today: bool
    weaving_boost_next_day: bool
    weaving_boost_multiplier_today: float
    global_accident_bonus: float
    pending_accident_bonus_next_day: float
    global_non_weaving_output_multiplier_today: float
    lockdown_today: bool


@dataclass(frozen=True)
class HiddenAccumulatorState:
    rigidity: float
    radical_potential: float
    innovation_pressure: float


@dataclass(frozen=True)
class PromptState:
    prompt_id: str
    kind: str
    tick: int
    choices: Tuple[str, ...]
    status: str
    selected_choice: str | None
    payload: Dict[str, Any]


@dataclass(frozen=True)
class ConflictState:
    discovered: Dict[str, bool]


@dataclass(frozen=True)
class SimSimState:
    day_tick: int
    phase: str
    time_label: str
    config_hash: str
    config_id: str
    assignments: Dict[str, int | None]
    assignment_template: Dict[int, WorkerAssignment]
    rooms: Dict[int, RoomState]
    supervisors: Dict[str, SupervisorState]
    inventory: InventoryState
    worker_pools: WorkerPoolState
    regime: RegimeState
    security_lead: str
    events: List[dict]
    prompts: List[PromptState]
    conflict: ConflictState
    hidden_accumulators: HiddenAccumulatorState
    next_event_id: int


@dataclass
class PipelineRoomRuntime:
    room_id: int
    supervisor: str | None
    assigned_dumb: int
    assigned_smart: int
    present_dumb: int = 0
    present_smart: int = 0
    absent_pct: float = 0.0
    stress_old: float = 0.0
    discipline_old: float = 0.0
    alignment_old: float = 0.0
    equipment_before: float = 1.0
    equipment_after_repair: float = 1.0
    equipment_after_damage: float = 1.0
    hours_effective: float = 9.0
    l_value: float = 0.4
    i_value: float = 0.0
    relief_sup: float = 0.0
    relief_event: float = 0.0
    relief_total: float = 0.0
    fiasco_severity: float = 0.0
    casualty_rate: float = 0.0
    accident_chance: float = 0.0
    accidents_count: int = 0
    casualties: int = 0
    outcome_label: str = "neutral"
    sup_mult: float = 1.0
    output_multiplier: float = 1.0
    equipment_damage: float = 0.0
    no_accidents: bool = False
    generic_accident_applied: bool = False
    base_cap_wu: float = 0.0
    prod_mult: float = 0.0
    output_wu: float = 0.0
    progress_p: float = 0.0
    output_today: Dict[str, int] = field(default_factory=lambda: _resource_zeroes())


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _resource_zeroes() -> Dict[str, int]:
    return {key: 0 for key in RESOURCE_KEYS}


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


def _stable_u64(seed: int, *parts: object) -> int:
    payload = "|".join([str(seed), *[str(p) for p in parts]])
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _rng01(seed: int, *parts: object) -> float:
    return _stable_u64(seed, *parts) / float(2**64)


def _rng_int(seed: int, low: int, high: int, *parts: object) -> int:
    if high <= low:
        return int(low)
    span = int(high) - int(low) + 1
    return int(low) + (_stable_u64(seed, *parts) % span)


def _stochastic_round(x: float, seed: int, *parts: object) -> int:
    n = int(x)
    frac = max(0.0, float(x) - float(n))
    return n + 1 if _rng01(seed, *parts) < frac else n


def _edge_key(a: str, b: str) -> str:
    left, right = sorted((a, b))
    return f"{left}-{right}"


def _rooms_edge_key(a_room: int, b_room: int) -> str:
    left, right = sorted((int(a_room), int(b_room)))
    return f"{left}-{right}"


class SimSimKernel:
    """Deterministic config-driven sim_sim kernel."""

    def __init__(self, seed: int, *, config_path: str | None = None) -> None:
        self._seed = int(seed)
        self._loaded_config: LoadedSimSimConfig = load_sim_sim_config(config_path)
        self._config = self._loaded_config.config

        initial_assignments = self._initial_assignments(day_tick=0)
        initial_worker_template = self._initial_worker_template(day_tick=0)

        supervisors = self._initial_supervisors(assignments=initial_assignments)
        rooms = self._initial_rooms(assignments=initial_assignments, template=initial_worker_template)

        bootstrap_event = {
            "tick": 0,
            "event_id": 0,
            "kind": "bootstrap",
            "details": {
                "schema": "sim_sim_1",
                "config_id": self._loaded_config.config_id,
                "config_hash": self._loaded_config.config_hash,
            },
        }

        self._state = SimSimState(
            day_tick=0,
            phase="planning",
            time_label="06:00",
            config_hash=self._loaded_config.config_hash,
            config_id=self._loaded_config.config_id,
            assignments=initial_assignments,
            assignment_template=initial_worker_template,
            rooms=rooms,
            supervisors=supervisors,
            inventory=InventoryState(
                cash=int(self._config.initial_state.cash),
                inventories={
                    key: int(self._config.initial_state.inventory.get(key, 0))
                    for key in RESOURCE_KEYS
                },
            ),
            worker_pools=WorkerPoolState(
                dumb_total=int(self._config.initial_state.worker_dumb),
                smart_total=int(self._config.initial_state.worker_smart),
            ),
            regime=RegimeState(
                refactor_days=0,
                inversion_days=0,
                shutdown_except_brewery_today=False,
                weaving_boost_next_day=False,
                weaving_boost_multiplier_today=1.0,
                global_accident_bonus=0.0,
                pending_accident_bonus_next_day=0.0,
                global_non_weaving_output_multiplier_today=1.0,
                lockdown_today=False,
            ),
            security_lead="L",
            events=[bootstrap_event],
            prompts=[],
            conflict=ConflictState(discovered={}),
            hidden_accumulators=HiddenAccumulatorState(
                rigidity=0.0,
                radical_potential=0.0,
                innovation_pressure=0.0,
            ),
            next_event_id=1,
        )

    @property
    def seed(self) -> int:
        return int(self._seed)

    @property
    def state(self) -> SimSimState:
        return self._state

    @property
    def loaded_config(self) -> LoadedSimSimConfig:
        return self._loaded_config

    def record_external_event(
        self,
        *,
        kind: str,
        details: Mapping[str, Any] | None = None,
        room_id: int | None = None,
        supervisor: str | None = None,
    ) -> None:
        event = {
            "tick": int(self._state.day_tick),
            "event_id": int(self._state.next_event_id),
            "kind": str(kind),
        }
        if room_id is not None:
            event["room_id"] = int(room_id)
        if supervisor is not None:
            event["supervisor"] = str(supervisor)
        if details:
            event["details"] = dict(details)

        self._state = SimSimState(
            day_tick=self._state.day_tick,
            phase=self._state.phase,
            time_label=self._state.time_label,
            config_hash=self._state.config_hash,
            config_id=self._state.config_id,
            assignments=dict(self._state.assignments),
            assignment_template=dict(self._state.assignment_template),
            rooms=dict(self._state.rooms),
            supervisors=dict(self._state.supervisors),
            inventory=self._state.inventory,
            worker_pools=self._state.worker_pools,
            regime=self._state.regime,
            security_lead=self._state.security_lead,
            events=self._state.events + [event],
            prompts=list(self._state.prompts),
            conflict=self._state.conflict,
            hidden_accumulators=self._state.hidden_accumulators,
            next_event_id=self._state.next_event_id + 1,
        )

    def _room_unlock_day(self, room_id: int) -> int:
        return int(self._config.unlock_schedule_rooms.get(int(room_id), -1))

    def _is_room_unlocked(self, room_id: int, day_tick: int) -> bool:
        if int(room_id) == 6:
            return False
        unlock_day = self._room_unlock_day(room_id)
        return unlock_day >= 0 and int(day_tick) >= unlock_day

    def _supervisor_unlock_day(self, code: str) -> int:
        return int(self._config.unlock_schedule_supervisors.get(code, 9999))

    def _is_supervisor_unlocked(self, code: str, day_tick: int) -> bool:
        return int(day_tick) >= self._supervisor_unlock_day(code)

    def _initial_assignments(self, *, day_tick: int) -> Dict[str, int | None]:
        assignments: Dict[str, int | None] = {}
        for profile in SUPERVISOR_PROFILES:
            if not self._is_supervisor_unlocked(profile.code, day_tick):
                continue
            assignments[profile.code] = profile.native_room if self._is_room_unlocked(profile.native_room, day_tick) else None
        assignments["L"] = 1
        return assignments

    def _initial_worker_template(self, *, day_tick: int) -> Dict[int, WorkerAssignment]:
        out: Dict[int, WorkerAssignment] = {}
        for room_id in ROOM_IDS:
            if room_id in (1, 6) or not self._is_room_unlocked(room_id, day_tick):
                out[room_id] = WorkerAssignment(dumb=0, smart=0)
            else:
                out[room_id] = WorkerAssignment(dumb=0, smart=0)
        return out

    def _initial_supervisors(self, *, assignments: Mapping[str, int | None]) -> Dict[str, SupervisorState]:
        out: Dict[str, SupervisorState] = {}
        for profile in SUPERVISOR_PROFILES:
            if not self._is_supervisor_unlocked(profile.code, 0):
                continue
            out[profile.code] = SupervisorState(
                code=profile.code,
                name=profile.name,
                unlocked_day=self._supervisor_unlock_day(profile.code),
                native_room=profile.native_room,
                assigned_room=assignments.get(profile.code),
                loyalty=0.55,
                confidence=0.5,
                influence=0.5,
                cooldown_days=0,
            )
        return out

    def _initial_rooms(
        self,
        *,
        assignments: Mapping[str, int | None],
        template: Mapping[int, WorkerAssignment],
    ) -> Dict[int, RoomState]:
        supervisor_by_room: Dict[int, str] = {}
        for code, room_id in assignments.items():
            if isinstance(room_id, int):
                supervisor_by_room[room_id] = code

        out: Dict[int, RoomState] = {}
        for room_id in ROOM_IDS:
            unlocked_day = self._room_unlock_day(room_id)
            locked = not self._is_room_unlocked(room_id, 0)
            if room_id == 1:
                out[room_id] = RoomState(
                    room_id=1,
                    name=ROOM_NAMES[1],
                    unlocked_day=0,
                    locked=False,
                    supervisor="L",
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

            if room_id == 6 or locked:
                out[room_id] = RoomState(
                    room_id=room_id,
                    name=ROOM_NAMES[room_id],
                    unlocked_day=unlocked_day,
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

            stress = self._initial_room_stress(room_id=room_id)
            assigned = template.get(room_id, WorkerAssignment(0, 0))
            out[room_id] = RoomState(
                room_id=room_id,
                name=ROOM_NAMES[room_id],
                unlocked_day=unlocked_day,
                locked=False,
                supervisor=supervisor_by_room.get(room_id),
                workers_assigned_dumb=assigned.dumb,
                workers_assigned_smart=assigned.smart,
                workers_present_dumb=assigned.dumb,
                workers_present_smart=assigned.smart,
                equipment_condition=float(self._config.initial_state.initial_equipment_condition),
                stress=stress,
                discipline=float(self._config.initial_state.initial_discipline),
                alignment=float(self._config.initial_state.initial_alignment),
                output_today=_resource_zeroes(),
                accidents_count=0,
                casualties=0,
            )

        return out

    def _initial_room_stress(self, *, room_id: int) -> float:
        lo = float(self._config.initial_state.initial_stress_min)
        hi = float(self._config.initial_state.initial_stress_max)
        if hi <= lo:
            return lo
        t = _rng01(self._seed, "init_stress", room_id)
        return lo + (hi - lo) * t

    def validate_day_input(self, day_input: DayInput, expected_tick_target: int) -> tuple[bool, str]:
        if day_input.tick_target != expected_tick_target:
            return False, f"tick_target must equal next day tick ({expected_tick_target})"
        if not day_input.advance:
            return False, "advance must be true"

        if self._state.phase not in ("planning", "close"):
            return False, f"inputs only accepted during planning/close; current phase={self._state.phase}"

        # Supervisor assignments.
        set_supervisors = self._normalize_supervisor_input(day_input)
        for room_id, code in set_supervisors.items():
            if int(room_id) not in ROOM_IDS:
                return False, f"room_id={room_id} is invalid"
            if room_id == 6:
                return False, "room_id=6 is permanently locked"
            if not self._is_room_unlocked(room_id, expected_tick_target):
                return False, f"room_id={room_id} not unlocked for day {expected_tick_target}"
            if code is None:
                continue
            if not self._is_supervisor_unlocked(code, expected_tick_target):
                return False, f"supervisor {code} not unlocked for day {expected_tick_target}"
            if room_id == 1 and code != "L":
                return False, "room1 accepts LIMEN only"
            if code == "L" and room_id != 1:
                return False, "LIMEN remains assigned to room1"

        # Worker proposals.
        for room_id, assignment in day_input.set_workers.items():
            if int(room_id) not in ROOM_IDS:
                return False, f"set_workers has invalid room_id={room_id}"
            if room_id in (1, 6):
                return False, f"room_id={room_id} does not accept workers"
            if not self._is_room_unlocked(room_id, expected_tick_target):
                return False, f"room_id={room_id} not unlocked for worker assignment"
            if assignment.dumb < 0 or assignment.smart < 0:
                return False, f"set_workers room_id={room_id} must be non-negative"

        eod = day_input.end_of_day
        for label, value in (
            ("sell_washed_dumb", eod.sell_washed_dumb),
            ("sell_washed_smart", eod.sell_washed_smart),
            ("convert_workers_dumb", eod.convert_workers_dumb),
            ("convert_workers_smart", eod.convert_workers_smart),
            ("upgrade_brains", eod.upgrade_brains),
        ):
            if int(value) < 0:
                return False, f"{label} must be >= 0"

        for response in day_input.prompt_responses:
            if not response.prompt_id:
                return False, "prompt_responses.prompt_id cannot be empty"
            if not response.choice:
                return False, "prompt_responses.choice cannot be empty"

        return True, "ok"

    def _normalize_supervisor_input(self, day_input: DayInput) -> Dict[int, str | None]:
        merged: Dict[int, str | None] = {}

        for room_id, code_raw in day_input.set_supervisors.items():
            code = resolve_supervisor_code(code_raw)
            merged[int(room_id)] = code

        for swap in day_input.supervisor_swaps:
            code = resolve_supervisor_code(swap.supervisor_code)
            merged[int(swap.room_id)] = code

        # Canon hard rule always enforced.
        merged[1] = "L"
        return merged

    def step(self, day_input: DayInput) -> tuple[SimSimState, SimSimState]:
        previous = self._state
        day = previous.day_tick + 1

        runtime_events: List[dict] = []
        runtime_prompts: List[PromptState] = []
        next_event_id = int(previous.next_event_id)

        def emit(kind: str, *, room_id: int | None = None, supervisor: str | None = None, details: Mapping[str, Any] | None = None) -> None:
            nonlocal next_event_id
            event: Dict[str, Any] = {"tick": int(day), "event_id": int(next_event_id), "kind": str(kind)}
            if room_id is not None:
                event["room_id"] = int(room_id)
            if supervisor is not None:
                event["supervisor"] = str(supervisor)
            if details:
                event["details"] = dict(details)
            runtime_events.append(event)
            next_event_id += 1

        # 1) Load start state.
        start = previous

        # 2) Validate supervisor assignments.
        assignments = self._compute_assignments(start, day_input=day_input, day=day, emit=emit)

        # 3) Validate worker proposal capacities + availability.
        proposed_workers = self._compute_worker_proposal(start, day_input=day_input, assignments=assignments, day=day, emit=emit)

        # 4) Determine security lead.
        security_lead = self._determine_security_lead(assignments)

        # 5) Compute hours (LIMEN penalty).
        hours, _ = self._compute_hours(start, security_lead=security_lead)

        # 6) Apply security redistribution.
        final_assigned, thrum_security_failed = self._apply_security_redistribution(
            start,
            proposed_workers=proposed_workers,
            assignments=assignments,
            security_lead=security_lead,
            day=day,
            emit=emit,
        )

        # 7) Absenteeism baseline + security attendance modifiers.
        absent_pct_by_room = self._compute_absenteeism(
            start,
            assigned=final_assigned,
            security_lead=security_lead,
            thrum_security_failed=thrum_security_failed,
        )

        # 8) Present workers per room.
        present_by_room = self._compute_present_workers(final_assigned=final_assigned, absent_pct_by_room=absent_pct_by_room)

        # 9) Detect hostile adjacency -> discovery/conflict (max 1/day).
        conflict_plan = self._schedule_conflict_or_discovery(
            start,
            assignments=assignments,
            day=day,
        )

        # 10) Resolve discovery/conflict now.
        conflict_resolution = self._resolve_conflict_or_discovery(
            start,
            plan=conflict_plan,
            day_input=day_input,
            day=day,
            emit=emit,
            prompts=runtime_prompts,
        )

        # 11) Compute base L/I/Rsup.
        runtime_rooms = self._build_runtime_rooms(
            start,
            day=day,
            assignments=assignments,
            final_assigned=final_assigned,
            present_by_room=present_by_room,
            absent_pct_by_room=absent_pct_by_room,
            hours=hours,
            conflict_resolution=conflict_resolution,
        )

        # 12) Apply repair-first actions.
        weaving_boost_pending = False
        weaving_boost_multiplier_pending = 1.0
        regime = self._prepare_regime_for_day(start.regime)
        self._apply_repair_first(runtime_rooms=runtime_rooms, regime=regime)

        # 13) Accident chances + supervisor-room outcomes.
        factory_deltas = {
            "stress": 0.0,
            "discipline": 0.0,
            "alignment": 0.0,
            "global_accident_bonus": 0.0,
            "equipment_damage_multiplier": 1.0,
        }
        outcome_by_supervisor: Dict[str, str] = {}
        self._resolve_supervisor_outcomes(
            runtime_rooms=runtime_rooms,
            regime=regime,
            day=day,
            emit=emit,
            factory_deltas=factory_deltas,
            outcome_by_supervisor=outcome_by_supervisor,
        )

        # 14) Generic accidents for non-overridden rooms.
        self._apply_generic_accidents(runtime_rooms=runtime_rooms, day=day, regime=regime, emit=emit)

        # 15) Apply equipment damage.
        self._apply_equipment_damage(runtime_rooms=runtime_rooms, damage_multiplier=factory_deltas["equipment_damage_multiplier"])

        # 16) Compute Cap_r.
        self._compute_base_capacity(runtime_rooms=runtime_rooms)

        # 17) Compute productivity multiplier.
        self._compute_productivity_multiplier(runtime_rooms=runtime_rooms, regime=regime)

        # 18) Apply supervisor multipliers + temp modifiers.
        for rr in runtime_rooms.values():
            if rr.room_id == 5 and start.regime.weaving_boost_next_day:
                rr.output_multiplier *= max(1.0, float(start.regime.weaving_boost_multiplier_today))
            if regime.shutdown_except_brewery_today and rr.room_id != 4:
                rr.output_multiplier = 0.0
            if regime.lockdown_today and rr.room_id not in (1, 6):
                rr.output_multiplier = 0.0
            if rr.room_id != 5:
                rr.output_multiplier *= float(regime.global_non_weaving_output_multiplier_today)

        # 19) Compute actual output O_r.
        for rr in runtime_rooms.values():
            rr.output_wu = max(0.0, rr.base_cap_wu * rr.prod_mult * rr.sup_mult * rr.output_multiplier)

        # 20) Convert outputs to units.
        inventory_after_units, output_by_room = self._convert_outputs_to_units(
            start,
            runtime_rooms=runtime_rooms,
            day=day,
        )

        # 21) Compute perceived progress P_r.
        self._compute_perceived_progress(runtime_rooms=runtime_rooms)

        # 22) Compute relief R_event + R_total.
        self._compute_relief(runtime_rooms=runtime_rooms)

        # 23) Update worker S/D/A via equations (sync update).
        self._update_worker_states(runtime_rooms=runtime_rooms, regime=regime)

        # 24) Update supervisor stats.
        supervisors_next = self._update_supervisors(
            start,
            assignments=assignments,
            outcomes=outcome_by_supervisor,
            conflict_resolution=conflict_resolution,
            factory_deltas=factory_deltas,
            emit=emit,
        )

        # 25) Critical event eligibility + prompt allow/suppress.
        critical_effects = self._handle_critical_events(
            day=day,
            supervisors=supervisors_next,
            assignments=assignments,
            day_input=day_input,
            regime=regime,
            hidden=start.hidden_accumulators,
            prompts=runtime_prompts,
            emit=emit,
        )
        hidden_after_critical = critical_effects["hidden"]
        regime = critical_effects["regime"]
        supervisors_next = critical_effects["supervisors"]

        # 26) Apply casualties to worker pools.
        casualties_total = sum(rr.casualties for rr in runtime_rooms.values())
        if day <= self._config.guardrails.early_days_casualty_cap_until_day:
            casualties_total = min(casualties_total, self._config.guardrails.early_days_max_casualties)
        worker_pools = WorkerPoolState(
            dumb_total=max(0, start.worker_pools.dumb_total - casualties_total),
            smart_total=max(0, start.worker_pools.smart_total),
        )

        # 27) End-of-day crafting: upgrades -> selling -> conversions.
        inventory_after_eod, worker_pools = self._apply_end_of_day_actions(
            inventory=inventory_after_units,
            worker_pools=worker_pools,
            actions=day_input.end_of_day,
            day=day,
            emit=emit,
        )

        if any(value > 0 for value in output_by_room.get(5, _resource_zeroes()).values()):
            weaving_boost_pending = True
            weaving_boost_multiplier_pending = max(weaving_boost_multiplier_pending, 1.2)

        # 28) Update hidden accumulators.
        hidden_next = self._update_hidden_accumulators(
            hidden=hidden_after_critical,
            runtime_rooms=runtime_rooms,
            security_lead=security_lead,
            output_by_room=output_by_room,
            upgrade_count=day_input.end_of_day.upgrade_brains,
            casualties=casualties_total,
        )

        # 29) Decrement durations; clear day flags.
        regime_next = RegimeState(
            refactor_days=max(0, regime.refactor_days - 1),
            inversion_days=max(0, regime.inversion_days - 1),
            shutdown_except_brewery_today=False,
            weaving_boost_next_day=weaving_boost_pending,
            weaving_boost_multiplier_today=weaving_boost_multiplier_pending,
            global_accident_bonus=max(0.0, regime.pending_accident_bonus_next_day),
            pending_accident_bonus_next_day=0.0,
            global_non_weaving_output_multiplier_today=1.0,
            lockdown_today=False,
        )

        supervisors_next = {
            code: SupervisorState(
                code=sup.code,
                name=sup.name,
                unlocked_day=sup.unlocked_day,
                native_room=sup.native_room,
                assigned_room=sup.assigned_room,
                loyalty=sup.loyalty,
                confidence=sup.confidence,
                influence=sup.influence,
                cooldown_days=max(0, sup.cooldown_days - 1),
            )
            for code, sup in supervisors_next.items()
        }

        # 30) Persist + increment day.
        rooms_next = self._finalize_rooms(
            day=day,
            assignments=assignments,
            runtime_rooms=runtime_rooms,
            output_by_room=output_by_room,
            supervisors=supervisors_next,
            previous=start.rooms,
        )

        assignment_template = {
            room_id: WorkerAssignment(
                dumb=int(final_assigned.get(room_id, WorkerAssignment(0, 0)).dumb),
                smart=int(final_assigned.get(room_id, WorkerAssignment(0, 0)).smart),
            )
            for room_id in ROOM_IDS
        }

        conflict_next = ConflictState(discovered=conflict_resolution["discovered_next"])

        # unlock events
        for room_id in ROOM_IDS:
            prev_locked = start.rooms[room_id].locked
            now_locked = rooms_next[room_id].locked
            if prev_locked and not now_locked:
                emit(
                    "room_unlocked",
                    room_id=room_id,
                    details={
                        "name": rooms_next[room_id].name,
                        "unlocked_day": rooms_next[room_id].unlocked_day,
                    },
                )
        for code, profile in SUPERVISOR_BY_CODE.items():
            if code in supervisors_next and code not in start.supervisors:
                emit(
                    "supervisor_unlocked",
                    supervisor=code,
                    room_id=profile.native_room,
                    details={
                        "name": profile.name,
                        "native_room": profile.native_room,
                        "unlocked_day": self._supervisor_unlock_day(code),
                    },
                )

        emit(
            "day_advanced",
            details={
                "day": day,
                "phase": "planning",
                "security_lead": security_lead,
                "config_id": self._loaded_config.config_id,
            },
        )

        self._state = SimSimState(
            day_tick=day,
            phase="planning",
            time_label=f"{6 + (day % 12):02d}:00",
            config_hash=self._loaded_config.config_hash,
            config_id=self._loaded_config.config_id,
            assignments=assignments,
            assignment_template=assignment_template,
            rooms=rooms_next,
            supervisors=supervisors_next,
            inventory=inventory_after_eod,
            worker_pools=worker_pools,
            regime=regime_next,
            security_lead=security_lead,
            events=start.events + runtime_events,
            prompts=runtime_prompts,
            conflict=conflict_next,
            hidden_accumulators=hidden_next,
            next_event_id=next_event_id,
        )

        return previous, self._state

    def _compute_assignments(
        self,
        start: SimSimState,
        *,
        day_input: DayInput,
        day: int,
        emit: Any,
    ) -> Dict[str, int | None]:
        assignments: Dict[str, int | None] = {}
        for profile in SUPERVISOR_PROFILES:
            if not self._is_supervisor_unlocked(profile.code, day):
                continue
            prev_room = start.assignments.get(profile.code)
            if isinstance(prev_room, int) and self._is_room_unlocked(prev_room, day) and prev_room != 6:
                assignments[profile.code] = prev_room
            elif self._is_room_unlocked(profile.native_room, day):
                assignments[profile.code] = profile.native_room
            else:
                assignments[profile.code] = None

        overrides = self._normalize_supervisor_input(day_input)
        for room_id, code in overrides.items():
            if room_id == 1:
                assignments["L"] = 1
                continue
            if not self._is_room_unlocked(room_id, day):
                continue
            if code is None:
                # remove existing occupant if any
                for sup_code, assigned_room in list(assignments.items()):
                    if assigned_room == room_id and sup_code != "L":
                        assignments[sup_code] = None
                continue

            if code == "L":
                assignments["L"] = 1
                continue

            # clear room occupant first
            for sup_code, assigned_room in list(assignments.items()):
                if assigned_room == room_id:
                    assignments[sup_code] = None
            assignments[code] = room_id

        assignments["L"] = 1

        # uniqueness per room (L owns room1).
        occupied: Dict[int, str] = {}
        for code in sorted(assignments.keys()):
            room_id = assignments.get(code)
            if room_id is None:
                continue
            if room_id in occupied:
                assignments[code] = None
                emit("assignment_resolved", supervisor=code, room_id=None, details={"reason": "room_occupied"})
            else:
                occupied[room_id] = code

        if 6 in occupied:
            offending = occupied[6]
            assignments[offending] = None
            emit("assignment_resolved", supervisor=offending, details={"reason": "room6_locked"})

        return assignments

    def _compute_worker_proposal(
        self,
        start: SimSimState,
        *,
        day_input: DayInput,
        assignments: Mapping[str, int | None],
        day: int,
        emit: Any,
    ) -> Dict[int, WorkerAssignment]:
        proposed: Dict[int, WorkerAssignment] = {
            room_id: WorkerAssignment(
                dumb=int(start.assignment_template.get(room_id, WorkerAssignment(0, 0)).dumb),
                smart=int(start.assignment_template.get(room_id, WorkerAssignment(0, 0)).smart),
            )
            for room_id in ROOM_IDS
        }

        for room_id, assignment in day_input.set_workers.items():
            if room_id in (1, 6) or not self._is_room_unlocked(room_id, day):
                continue
            proposed[room_id] = WorkerAssignment(dumb=max(0, int(assignment.dumb)), smart=max(0, int(assignment.smart)))

        # capacity validation/clamp by room
        for room_id in ROOM_IDS:
            cap = self._config.room_capacities.get(room_id)
            p = proposed.get(room_id, WorkerAssignment(0, 0))
            if cap is None or room_id in (1, 6) or not self._is_room_unlocked(room_id, day):
                proposed[room_id] = WorkerAssignment(0, 0)
                continue
            dumb = min(max(0, p.dumb), cap.max_dumb)
            smart = min(max(0, p.smart), cap.max_smart)
            total = dumb + smart
            if total > cap.max_total:
                overflow = total - cap.max_total
                # deterministic trim: smart first for lower-volume capacity rooms.
                trim_smart = min(smart, overflow)
                smart -= trim_smart
                overflow -= trim_smart
                if overflow > 0:
                    dumb = max(0, dumb - overflow)
                emit("worker_proposal_clamped", room_id=room_id, details={"reason": "capacity"})
            proposed[room_id] = WorkerAssignment(dumb=dumb, smart=smart)

        # availability clamp across all rooms
        total_dumb = sum(v.dumb for rid, v in proposed.items() if rid not in (1, 6))
        total_smart = sum(v.smart for rid, v in proposed.items() if rid not in (1, 6))
        avail_dumb = int(start.worker_pools.dumb_total)
        avail_smart = int(start.worker_pools.smart_total)

        if total_dumb > avail_dumb:
            overflow = total_dumb - avail_dumb
            for room_id in (5, 4, 3, 2):
                current = proposed[room_id]
                cut = min(current.dumb, overflow)
                proposed[room_id] = WorkerAssignment(current.dumb - cut, current.smart)
                overflow -= cut
                if overflow <= 0:
                    break
            emit("worker_proposal_clamped", details={"reason": "dumb_availability"})

        if total_smart > avail_smart:
            overflow = total_smart - avail_smart
            for room_id in (5, 4, 3, 2):
                current = proposed[room_id]
                cut = min(current.smart, overflow)
                proposed[room_id] = WorkerAssignment(current.dumb, current.smart - cut)
                overflow -= cut
                if overflow <= 0:
                    break
            emit("worker_proposal_clamped", details={"reason": "smart_availability"})

        # rooms without supervisor are still allowed workers (player intent), no extra constraints here.
        return proposed

    def _determine_security_lead(self, assignments: Mapping[str, int | None]) -> str:
        for code, room_id in assignments.items():
            if room_id == 1:
                return code
        return "C"

    def _compute_hours(self, start: SimSimState, *, security_lead: str) -> tuple[float, int]:
        limen_security_count = 0
        for ev in start.events:
            if ev.get("kind") == "limen_security_counted":
                limen_security_count += 1

        hours = 9.0
        if security_lead == "L":
            limen_security_count += 1
            hours = 9.0 - min(2.0, float(limen_security_count))
        return max(1.0, hours), limen_security_count

    def _apply_security_redistribution(
        self,
        start: SimSimState,
        *,
        proposed_workers: Mapping[int, WorkerAssignment],
        assignments: Mapping[str, int | None],
        security_lead: str,
        day: int,
        emit: Any,
    ) -> tuple[Dict[int, WorkerAssignment], bool]:
        assigned: Dict[int, WorkerAssignment] = {
            room_id: WorkerAssignment(v.dumb, v.smart)
            for room_id, v in proposed_workers.items()
        }

        thrum_failed = False

        def pop_from_room(room_id: int, *, dumb: int = 0, smart: int = 0) -> tuple[int, int]:
            current = assigned.get(room_id, WorkerAssignment(0, 0))
            out_d = min(current.dumb, dumb)
            out_s = min(current.smart, smart)
            assigned[room_id] = WorkerAssignment(current.dumb - out_d, current.smart - out_s)
            return out_d, out_s

        def add_to_room(room_id: int, *, dumb: int = 0, smart: int = 0) -> None:
            cap = self._config.room_capacities.get(room_id)
            if cap is None:
                return
            current = assigned.get(room_id, WorkerAssignment(0, 0))
            next_d = min(cap.max_dumb, current.dumb + dumb)
            next_s = min(cap.max_smart, current.smart + smart)
            total = next_d + next_s
            if total > cap.max_total:
                overflow = total - cap.max_total
                if next_s >= overflow:
                    next_s -= overflow
                else:
                    overflow -= next_s
                    next_s = 0
                    next_d = max(0, next_d - overflow)
            assigned[room_id] = WorkerAssignment(next_d, next_s)

        def unassigned_pool() -> WorkerAssignment:
            used_d = sum(v.dumb for rid, v in assigned.items() if rid not in (1, 6))
            used_s = sum(v.smart for rid, v in assigned.items() if rid not in (1, 6))
            return WorkerAssignment(
                dumb=max(0, start.worker_pools.dumb_total - used_d),
                smart=max(0, start.worker_pools.smart_total - used_s),
            )

        if security_lead == "L":
            return assigned, thrum_failed

        if security_lead == "S":
            pool = unassigned_pool()
            cap = self._config.room_capacities[2]
            cur = assigned.get(2, WorkerAssignment(0, 0))
            need_total = max(0, cap.max_total - (cur.dumb + cur.smart))
            if need_total > 0:
                take_smart = min(pool.smart, need_total)
                need_total -= take_smart
                take_dumb = min(pool.dumb, need_total)
                add_to_room(2, dumb=take_dumb, smart=take_smart)
            # pull from low-priority rooms if still not full
            cur = assigned.get(2, WorkerAssignment(0, 0))
            need_total = max(0, cap.max_total - (cur.dumb + cur.smart))
            for room_id in self._config.security.stiletto_pull_order:
                if need_total <= 0:
                    break
                moved = pop_from_room(room_id, dumb=need_total, smart=need_total)
                add_to_room(2, dumb=moved[0], smart=moved[1])
                cur = assigned.get(2, WorkerAssignment(0, 0))
                need_total = max(0, cap.max_total - (cur.dumb + cur.smart))
            emit("security_redistribution", supervisor="S", details={"mode": "fill_conveyor"})
            return assigned, thrum_failed

        if security_lead == "W":
            pool = unassigned_pool()
            # prioritize smart into brewery then weaving
            for room_id in (4, 5):
                cap = self._config.room_capacities[room_id]
                cur = assigned.get(room_id, WorkerAssignment(0, 0))
                need_smart = max(0, cap.max_smart - cur.smart)
                give = min(pool.smart, need_smart)
                if give > 0:
                    add_to_room(room_id, smart=give)
                    pool = WorkerAssignment(pool.dumb, pool.smart - give)
            # then steal from theatres/conveyor
            for from_room in self._config.security.witch_pull_order:
                if pool.smart > 0:
                    continue
                moved = pop_from_room(from_room, smart=1)
                if moved[1] > 0:
                    add_to_room(4, smart=moved[1])
            emit("security_redistribution", supervisor="W", details={"mode": "brewery_weaving_smart"})
            return assigned, thrum_failed

        # CATHEXIS and THRUM chaos modes.
        keep_bias = self._config.security.random_keep_bias_cathexis
        if security_lead == "T":
            failed_roll = _rng01(self._seed, day, "thrum_security") < self._config.security.thrum_failure_chance
            thrum_failed = bool(failed_roll)
            keep_bias = self._config.security.random_keep_bias_thrum_success if not thrum_failed else self._config.security.random_keep_bias_cathexis

        unlocked_rooms = [room_id for room_id in (2, 3, 4, 5) if self._is_room_unlocked(room_id, day)]

        pool_d = 0
        pool_s = 0
        for room_id in unlocked_rooms:
            current = assigned.get(room_id, WorkerAssignment(0, 0))
            keep_d = int(current.dumb * keep_bias)
            keep_s = int(current.smart * keep_bias)
            pool_d += current.dumb - keep_d
            pool_s += current.smart - keep_s
            assigned[room_id] = WorkerAssignment(keep_d, keep_s)

        # include currently unassigned workers
        unassigned = unassigned_pool()
        pool_d += unassigned.dumb
        pool_s += unassigned.smart

        for worker_type in ("smart", "dumb"):
            for idx in range(2048):
                if worker_type == "smart":
                    if pool_s <= 0:
                        break
                else:
                    if pool_d <= 0:
                        break

                # deterministic pseudo-random room pick
                room_idx = int(_rng01(self._seed, day, security_lead, worker_type, idx) * len(unlocked_rooms))
                target_room = unlocked_rooms[min(room_idx, len(unlocked_rooms) - 1)]
                cap = self._config.room_capacities[target_room]
                current = assigned[target_room]
                if worker_type == "smart":
                    if current.smart >= cap.max_smart or (current.smart + current.dumb) >= cap.max_total:
                        continue
                    assigned[target_room] = WorkerAssignment(current.dumb, current.smart + 1)
                    pool_s -= 1
                else:
                    if current.dumb >= cap.max_dumb or (current.smart + current.dumb) >= cap.max_total:
                        continue
                    assigned[target_room] = WorkerAssignment(current.dumb + 1, current.smart)
                    pool_d -= 1

        emit(
            "security_redistribution",
            supervisor=security_lead,
            details={"mode": "chaos", "thrum_failed": thrum_failed},
        )
        return assigned, thrum_failed

    def _compute_absenteeism(
        self,
        start: SimSimState,
        *,
        assigned: Mapping[int, WorkerAssignment],
        security_lead: str,
        thrum_security_failed: bool,
    ) -> Dict[int, float]:
        out: Dict[int, float] = {}

        weighted_disc = 0.0
        weighted_n = 0
        for room_id in (2, 3, 4, 5):
            room = start.rooms.get(room_id)
            if not room or room.locked:
                continue
            planned = assigned.get(room_id, WorkerAssignment(0, 0))
            n = planned.dumb + planned.smart
            if n <= 0:
                continue
            weighted_disc += n * float(room.discipline if room.discipline is not None else 0.5)
            weighted_n += n
        d_factory = (weighted_disc / max(1, weighted_n)) if weighted_n > 0 else 0.5

        absent_bonus = 0.0
        if security_lead in ("C", "T"):
            absent_bonus = _clamp01(
                self._config.security.c_or_t_absent_bonus_base
                + self._config.security.c_or_t_absent_bonus_scale * (1.0 - d_factory)
            )
            if security_lead == "T" and thrum_security_failed:
                absent_bonus = _clamp01(absent_bonus + self._config.security.thrum_failure_extra_absent_flat)
            elif security_lead == "T" and not thrum_security_failed:
                absent_bonus = 0.0

        for room_id in ROOM_IDS:
            if room_id in (1, 6):
                out[room_id] = 0.0
                continue
            room = start.rooms.get(room_id)
            if room is None or room.locked:
                out[room_id] = 0.0
                continue
            stress = float(room.stress if room.stress is not None else 0.0)
            discipline = float(room.discipline if room.discipline is not None else 0.5)
            base = self._config.absenteeism.base
            pct = _clamp01(
                base
                + self._config.absenteeism.stress_coeff * stress
                - self._config.absenteeism.discipline_coeff * discipline
            )
            out[room_id] = _clamp01(pct + absent_bonus)

        return out

    def _compute_present_workers(
        self,
        *,
        final_assigned: Mapping[int, WorkerAssignment],
        absent_pct_by_room: Mapping[int, float],
    ) -> Dict[int, WorkerAssignment]:
        out: Dict[int, WorkerAssignment] = {}
        for room_id in ROOM_IDS:
            assigned = final_assigned.get(room_id, WorkerAssignment(0, 0))
            absent = float(absent_pct_by_room.get(room_id, 0.0))
            if room_id in (1, 6):
                out[room_id] = WorkerAssignment(0, 0)
                continue
            out[room_id] = WorkerAssignment(
                dumb=max(0, int(assigned.dumb * (1.0 - absent))),
                smart=max(0, int(assigned.smart * (1.0 - absent))),
            )
        return out

    def _schedule_conflict_or_discovery(
        self,
        start: SimSimState,
        *,
        assignments: Mapping[str, int | None],
        day: int,
    ) -> Dict[str, Any]:
        sup_to_room = {code: room for code, room in assignments.items() if isinstance(room, int)}
        hostile_pairs = list(self._config.conflicts.hostile_pairs)

        discovered = dict(start.conflict.discovered)
        discoveries: List[Dict[str, Any]] = []
        conflicts: List[Dict[str, Any]] = []

        for a, b in hostile_pairs:
            room_a = sup_to_room.get(a)
            room_b = sup_to_room.get(b)
            if room_a is None or room_b is None:
                continue
            if room_b not in ROOM_NEIGHBORS.get(room_a, ()):
                continue

            edge_sup = _edge_key(a, b)
            edge_room = _rooms_edge_key(room_a, room_b)
            payload = {
                "pair": (a, b),
                "room_pair": (room_a, room_b),
                "edge_sup": edge_sup,
                "edge_room": edge_room,
            }
            if discovered.get(edge_sup):
                conflicts.append(payload)
            else:
                discoveries.append(payload)

        if conflicts:
            ranked = sorted(
                conflicts,
                key=lambda item: (
                    -self._conflict_priority(item["room_pair"]),
                    item["edge_room"],
                ),
            )
            return {"kind": "conflict", "payload": ranked[0], "discovered": discovered}

        if discoveries:
            chosen = sorted(discoveries, key=lambda item: item["edge_room"])[0]
            return {"kind": "discovery", "payload": chosen, "discovered": discovered}

        return {"kind": "none", "payload": None, "discovered": discovered}

    def _conflict_priority(self, room_pair: Tuple[int, int]) -> int:
        if 1 in room_pair:
            return int(self._config.conflicts.security_edge_priority)
        return int(self._config.conflicts.edge_priority.get(_rooms_edge_key(room_pair[0], room_pair[1]), 0))

    def _resolve_conflict_or_discovery(
        self,
        start: SimSimState,
        *,
        plan: Mapping[str, Any],
        day_input: DayInput,
        day: int,
        emit: Any,
        prompts: List[PromptState],
    ) -> Dict[str, Any]:
        discovered = dict(plan["discovered"])
        conflict_room_l_delta: Dict[int, float] = {}
        conflict_room_i_delta: Dict[int, float] = {}
        supervisor_deltas: Dict[str, Dict[str, float]] = {}

        def sup_delta(code: str, field: str, delta: float) -> None:
            supervisor_deltas.setdefault(code, {}).setdefault(field, 0.0)
            supervisor_deltas[code][field] += float(delta)

        kind = str(plan["kind"])
        payload = plan.get("payload")
        if kind == "none" or not isinstance(payload, Mapping):
            return {
                "discovered_next": discovered,
                "room_l_delta": conflict_room_l_delta,
                "room_i_delta": conflict_room_i_delta,
                "supervisor_deltas": supervisor_deltas,
                "conflict_winner": None,
                "factory_side_effects": {"stress": 0.0, "discipline": 0.0, "alignment": 0.0, "global_accident_bonus": 0.0},
            }

        pair = tuple(payload["pair"])
        room_pair = tuple(payload["room_pair"])
        edge_sup = str(payload["edge_sup"])

        if kind == "discovery":
            discovered[edge_sup] = True
            for room_id in room_pair:
                conflict_room_l_delta[int(room_id)] = conflict_room_l_delta.get(int(room_id), 0.0)
            for code in pair:
                sup_delta(str(code), "loyalty", self._config.conflicts.discovered_loyalty_delta)
            emit(
                "conflict_discovered",
                details={
                    "pair": list(pair),
                    "room_pair": list(room_pair),
                    "discipline_delta": self._config.conflicts.discovered_discipline_delta,
                },
            )
            return {
                "discovered_next": discovered,
                "room_l_delta": conflict_room_l_delta,
                "room_i_delta": conflict_room_i_delta,
                "supervisor_deltas": supervisor_deltas,
                "conflict_winner": None,
                "factory_side_effects": {"stress": 0.0, "discipline": self._config.conflicts.discovered_discipline_delta, "alignment": 0.0, "global_accident_bonus": 0.0},
            }

        # conflict event
        prompt_id = f"prompt_conflict_{day}_{edge_sup.replace('-', '_')}"
        choices = ("support_A", "support_B", "suppress")

        selected = None
        responses = {r.prompt_id: r.choice for r in day_input.prompt_responses}
        selected = responses.get(prompt_id)
        if selected not in choices:
            selected = "support_A"

        prompts.append(
            PromptState(
                prompt_id=prompt_id,
                kind="conflict",
                tick=day,
                choices=choices,
                status="resolved",
                selected_choice=selected,
                payload={"pair": list(pair), "room_pair": list(room_pair)},
            )
        )

        if selected == "support_B":
            winner = str(pair[1])
            loser = str(pair[0])
            winner_room = int(room_pair[1])
            loser_room = int(room_pair[0])
        elif selected == "suppress":
            winner = str(pair[0])
            loser = str(pair[1])
            winner_room = int(room_pair[0])
            loser_room = int(room_pair[1])
        else:
            winner = str(pair[0])
            loser = str(pair[1])
            winner_room = int(room_pair[0])
            loser_room = int(room_pair[1])

        sup_delta(winner, "confidence", self._config.conflicts.support_confidence_delta)
        sup_delta(winner, "influence", self._config.conflicts.support_influence_delta)
        sup_delta(winner, "loyalty", self._config.conflicts.support_loyalty_delta)

        sup_delta(loser, "confidence", self._config.conflicts.oppose_confidence_delta)
        sup_delta(loser, "influence", self._config.conflicts.oppose_influence_delta)
        sup_delta(loser, "loyalty", self._config.conflicts.oppose_loyalty_delta)

        conflict_room_l_delta[winner_room] = conflict_room_l_delta.get(winner_room, 0.0) + 0.1
        conflict_room_l_delta[loser_room] = conflict_room_l_delta.get(loser_room, 0.0) - 0.1

        # ideology shift on loser room toward winner ideology sign.
        winner_i = self._config.lookup_tables.indoctrination_pressure.get(winner, {}).get(winner_room, 0.0)
        conflict_room_i_delta[loser_room] = conflict_room_i_delta.get(loser_room, 0.0) + (
            self._config.conflicts.support_confidence_delta * (1 if winner_i >= 0 else -1) * self._config.conflicts.ideology_shift
        )

        side_fx = {"stress": 0.0, "discipline": 0.0, "alignment": 0.0, "global_accident_bonus": 0.0}
        if winner == "L":
            side_fx["discipline"] += 0.03
            side_fx["alignment"] += 0.01
            side_fx["stress"] += 0.02
        elif winner == "S":
            side_fx["stress"] += 0.05
        elif winner == "C":
            side_fx["alignment"] -= 0.05
            side_fx["stress"] -= 0.02
            side_fx["discipline"] -= 0.03
        elif winner == "T":
            side_fx["stress"] -= 0.05
            side_fx["discipline"] -= 0.02

        emit(
            "conflict_event",
            supervisor=winner,
            details={
                "pair": list(pair),
                "winner": winner,
                "loser": loser,
                "choice": selected,
            },
        )

        return {
            "discovered_next": discovered,
            "room_l_delta": conflict_room_l_delta,
            "room_i_delta": conflict_room_i_delta,
            "supervisor_deltas": supervisor_deltas,
            "conflict_winner": winner,
            "factory_side_effects": side_fx,
        }

    def _build_runtime_rooms(
        self,
        start: SimSimState,
        *,
        day: int,
        assignments: Mapping[str, int | None],
        final_assigned: Mapping[int, WorkerAssignment],
        present_by_room: Mapping[int, WorkerAssignment],
        absent_pct_by_room: Mapping[int, float],
        hours: float,
        conflict_resolution: Mapping[str, Any],
    ) -> Dict[int, PipelineRoomRuntime]:
        supervisor_by_room: Dict[int, str] = {}
        for sup, room_id in assignments.items():
            if isinstance(room_id, int):
                supervisor_by_room[room_id] = sup

        runtime: Dict[int, PipelineRoomRuntime] = {}
        for room_id in ROOM_IDS:
            if room_id in (1, 6) or not self._is_room_unlocked(room_id, day):
                runtime[room_id] = PipelineRoomRuntime(
                    room_id=room_id,
                    supervisor=supervisor_by_room.get(room_id),
                    assigned_dumb=0,
                    assigned_smart=0,
                    present_dumb=0,
                    present_smart=0,
                    hours_effective=hours,
                )
                continue

            prev_room = start.rooms.get(room_id)
            stress = float(prev_room.stress if prev_room and prev_room.stress is not None else self._initial_room_stress(room_id=room_id))
            discipline = float(
                prev_room.discipline if prev_room and prev_room.discipline is not None else self._config.initial_state.initial_discipline
            )
            alignment = float(
                prev_room.alignment if prev_room and prev_room.alignment is not None else self._config.initial_state.initial_alignment
            )
            equipment = float(
                prev_room.equipment_condition
                if prev_room and prev_room.equipment_condition is not None
                else self._config.initial_state.initial_equipment_condition
            )

            assigned = final_assigned.get(room_id, WorkerAssignment(0, 0))
            present = present_by_room.get(room_id, WorkerAssignment(0, 0))

            sup = supervisor_by_room.get(room_id)
            l_table = self._config.lookup_tables.leadership_order.get(sup or "", {})
            i_table = self._config.lookup_tables.indoctrination_pressure.get(sup or "", {})
            l_value = float(l_table.get(room_id, self._config.lookup_tables.default_l))
            i_value = float(i_table.get(room_id, self._config.lookup_tables.default_i))
            l_value = _clamp01(l_value + float(conflict_resolution.get("room_l_delta", {}).get(room_id, 0.0)))
            i_value = float(i_value + float(conflict_resolution.get("room_i_delta", {}).get(room_id, 0.0)))

            relief_row = self._config.lookup_tables.relief_baseline.get(sup or "", {})
            relief_sup = float(relief_row.get(str(room_id), relief_row.get("default", self._config.lookup_tables.default_relief)))

            runtime[room_id] = PipelineRoomRuntime(
                room_id=room_id,
                supervisor=sup,
                assigned_dumb=assigned.dumb,
                assigned_smart=assigned.smart,
                present_dumb=present.dumb,
                present_smart=present.smart,
                absent_pct=float(absent_pct_by_room.get(room_id, 0.0)),
                stress_old=stress,
                discipline_old=discipline,
                alignment_old=alignment,
                equipment_before=equipment,
                equipment_after_repair=equipment,
                equipment_after_damage=equipment,
                hours_effective=hours,
                l_value=l_value,
                i_value=i_value,
                relief_sup=relief_sup,
                output_today=_resource_zeroes(),
            )

        return runtime

    def _prepare_regime_for_day(self, regime: RegimeState) -> RegimeState:
        return RegimeState(
            refactor_days=max(0, int(regime.refactor_days)),
            inversion_days=max(0, int(regime.inversion_days)),
            shutdown_except_brewery_today=bool(regime.shutdown_except_brewery_today),
            weaving_boost_next_day=bool(regime.weaving_boost_next_day),
            weaving_boost_multiplier_today=float(regime.weaving_boost_multiplier_today),
            global_accident_bonus=float(regime.global_accident_bonus),
            pending_accident_bonus_next_day=float(regime.pending_accident_bonus_next_day),
            global_non_weaving_output_multiplier_today=float(regime.global_non_weaving_output_multiplier_today),
            lockdown_today=bool(regime.lockdown_today),
        )

    def _apply_repair_first(self, *, runtime_rooms: Mapping[int, PipelineRoomRuntime], regime: RegimeState) -> None:
        for rr in runtime_rooms.values():
            if rr.room_id in (1, 6):
                continue
            if rr.supervisor == "W":
                missing = max(0.0, 1.0 - rr.equipment_after_repair)
                repair_hours = min(9.0, missing / 0.1)
                rr.equipment_after_repair = _clamp01(rr.equipment_after_repair + repair_hours * 0.1)
                rr.hours_effective = max(0.0, 9.0 - repair_hours)
            if rr.supervisor == "T" and rr.room_id == 5:
                rr.equipment_after_repair = 1.0
                rr.sup_mult = 0.0
                rr.output_multiplier *= 0.0

    def _resolve_supervisor_outcomes(
        self,
        *,
        runtime_rooms: Mapping[int, PipelineRoomRuntime],
        regime: RegimeState,
        day: int,
        emit: Any,
        factory_deltas: MutableMapping[str, float],
        outcome_by_supervisor: MutableMapping[str, str],
    ) -> None:
        for rr in runtime_rooms.values():
            if rr.room_id in (1, 6):
                continue
            present_total = rr.present_dumb + rr.present_smart
            if present_total <= 0:
                rr.outcome_label = "neutral"
                rr.accident_chance = 0.0
                rr.sup_mult = 0.0
                continue

            rr.accident_chance = _clamp01(
                self._config.accident.base
                + self._config.accident.low_discipline_coeff * (1.0 - rr.discipline_old)
                + self._config.accident.high_stress_coeff * rr.stress_old
                + self._config.accident.low_equipment_coeff * (1.0 - rr.equipment_after_repair)
                + regime.global_accident_bonus
            )

            outcomes = self._config.outcome_tables.get(rr.supervisor or "", {}).get(rr.room_id)
            if outcomes:
                row = self._choose_outcome(outcomes, day=day, room_id=rr.room_id, supervisor=rr.supervisor or "")
                rr.outcome_label = str(row.get("label", "neutral"))
                rr.sup_mult = float(row.get("sup_mult", 1.0))
                rr.fiasco_severity = float(row.get("fiasco_severity", 0.0))
                rr.no_accidents = bool(row.get("no_accidents", False))

                cas_min = int(row.get("casualties_min", 0))
                cas_max = int(row.get("casualties_max", cas_min))
                rr.casualties = _rng_int(self._seed, cas_min, cas_max, "casualty", day, rr.room_id, rr.supervisor or "")
                rr.accidents_count = 1 if rr.casualties > 0 or rr.fiasco_severity > 0 else 0

                dmg_min = float(row.get("equipment_damage_min", 0.0))
                dmg_max = float(row.get("equipment_damage_max", dmg_min))
                if dmg_max > 0.0:
                    t = _rng01(self._seed, "equip", day, rr.room_id, rr.supervisor or "")
                    rr.equipment_damage = dmg_min + (dmg_max - dmg_min) * t

                if bool(row.get("repair_all_equipment", False)):
                    for target in runtime_rooms.values():
                        if target.room_id in (2, 3, 4, 5):
                            target.equipment_after_repair = 1.0
                if float(row.get("factory_stress_delta", 0.0)) != 0.0:
                    factory_deltas["stress"] += float(row.get("factory_stress_delta", 0.0))
                if float(row.get("factory_discipline_delta", 0.0)) != 0.0:
                    factory_deltas["discipline"] += float(row.get("factory_discipline_delta", 0.0))
                if float(row.get("factory_alignment_delta", 0.0)) != 0.0:
                    factory_deltas["alignment"] += float(row.get("factory_alignment_delta", 0.0))

                if bool(row.get("weaving_boost_next_day", False)):
                    rr.output_multiplier *= float(row.get("weaving_boost_next_day", 1.0))

                emit(
                    "room_outcome",
                    room_id=rr.room_id,
                    supervisor=rr.supervisor,
                    details={
                        "label": rr.outcome_label,
                        "sup_mult": rr.sup_mult,
                        "fiasco": rr.fiasco_severity,
                    },
                )
            else:
                rr.outcome_label = "neutral"
                rr.sup_mult = 1.0
                rr.fiasco_severity = 0.0
                rr.casualties = 0
                rr.accidents_count = 0

            if rr.supervisor:
                outcome_by_supervisor[rr.supervisor] = rr.outcome_label

    def _choose_outcome(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        day: int,
        room_id: int,
        supervisor: str,
    ) -> Mapping[str, Any]:
        total_weight = 0.0
        for row in rows:
            total_weight += max(0.0, float(row.get("weight", 0.0)))
        if total_weight <= 0.0:
            return rows[0]
        roll = _rng01(self._seed, "outcome", day, room_id, supervisor) * total_weight
        acc = 0.0
        for row in rows:
            acc += max(0.0, float(row.get("weight", 0.0)))
            if roll <= acc:
                return row
        return rows[-1]

    def _apply_generic_accidents(self, *, runtime_rooms: Mapping[int, PipelineRoomRuntime], day: int, regime: RegimeState, emit: Any) -> None:
        for rr in runtime_rooms.values():
            if rr.room_id in (1, 6):
                continue
            if rr.no_accidents:
                rr.accidents_count = 0
                rr.casualties = 0
                continue
            if rr.accidents_count > 0:
                continue
            roll = _rng01(self._seed, "generic_accident", day, rr.room_id)
            if roll < rr.accident_chance:
                rr.generic_accident_applied = True
                rr.accidents_count = 1
                rr.casualties = max(rr.casualties, 1 if rr.fiasco_severity >= 0.5 else 0)
                rr.equipment_damage += 0.05 + 0.15 * _rng01(self._seed, "generic_damage", day, rr.room_id)
                emit(
                    "accident",
                    room_id=rr.room_id,
                    supervisor=rr.supervisor,
                    details={"generic": True, "casualties": rr.casualties},
                )

    def _apply_equipment_damage(self, *, runtime_rooms: Mapping[int, PipelineRoomRuntime], damage_multiplier: float) -> None:
        mult = max(0.1, float(damage_multiplier))
        for rr in runtime_rooms.values():
            if rr.room_id in (1, 6):
                rr.equipment_after_damage = 1.0 if rr.room_id == 1 else 0.0
                continue
            rr.equipment_after_damage = _clamp01(rr.equipment_after_repair - rr.equipment_damage * mult)

    def _compute_base_capacity(self, *, runtime_rooms: Mapping[int, PipelineRoomRuntime]) -> None:
        for rr in runtime_rooms.values():
            if rr.room_id in (1, 6):
                rr.base_cap_wu = 0.0
                continue
            base_rate = float(self._config.base_rate_wu_by_room.get(rr.room_id, 0.0))
            rr.base_cap_wu = max(0.0, base_rate * (rr.hours_effective / 9.0) * rr.equipment_after_damage)

    def _compute_productivity_multiplier(self, *, runtime_rooms: Mapping[int, PipelineRoomRuntime], regime: RegimeState) -> None:
        for rr in runtime_rooms.values():
            if rr.room_id in (1, 6):
                rr.prod_mult = 0.0
                continue
            if regime.refactor_days > 0:
                rr.prod_mult = _clamp01(
                    self._config.productivity.refactor_base
                    + self._config.productivity.refactor_discipline_coeff * rr.discipline_old
                    - self._config.productivity.refactor_stress_coeff * rr.stress_old
                )
            else:
                rr.prod_mult = _clamp01(
                    self._config.productivity.base
                    + self._config.productivity.discipline_coeff * rr.discipline_old
                    - self._config.productivity.stress_coeff * rr.stress_old
                )

    def _convert_outputs_to_units(
        self,
        start: SimSimState,
        *,
        runtime_rooms: Mapping[int, PipelineRoomRuntime],
        day: int,
    ) -> tuple[InventoryState, Dict[int, Dict[str, int]]]:
        inv = dict(start.inventory.inventories)
        output_by_room: Dict[int, Dict[str, int]] = {room_id: _resource_zeroes() for room_id in ROOM_IDS}

        conveyor = runtime_rooms.get(2)
        theatre = runtime_rooms.get(3)
        brewery = runtime_rooms.get(4)
        weaving = runtime_rooms.get(5)

        raw_total = 0
        raw_smart = 0
        raw_dumb = 0
        if conveyor:
            raw_total = max(0, _stochastic_round(conveyor.output_wu * self._config.economy.brains_per_wu, self._seed, "raw", day))
            present_total = max(1, conveyor.present_dumb + conveyor.present_smart)
            smart_share = conveyor.present_smart / present_total
            raw_smart = int(round(raw_total * smart_share))
            raw_smart = max(0, min(raw_total, raw_smart))
            raw_dumb = raw_total - raw_smart
            output_by_room[2]["raw_brains_dumb"] += raw_dumb
            output_by_room[2]["raw_brains_smart"] += raw_smart

        inv["raw_brains_dumb"] = inv.get("raw_brains_dumb", 0) + raw_dumb
        inv["raw_brains_smart"] = inv.get("raw_brains_smart", 0) + raw_smart

        if theatre:
            wash_capacity = max(
                0,
                _stochastic_round(
                    theatre.output_wu * self._config.economy.wash_capacity_per_wu,
                    self._seed,
                    "wash",
                    day,
                ),
            )
            wash_smart = min(inv.get("raw_brains_smart", 0), wash_capacity)
            wash_capacity -= wash_smart
            wash_dumb = min(inv.get("raw_brains_dumb", 0), wash_capacity)

            inv["raw_brains_smart"] -= wash_smart
            inv["raw_brains_dumb"] -= wash_dumb
            inv["washed_smart"] = inv.get("washed_smart", 0) + wash_smart
            inv["washed_dumb"] = inv.get("washed_dumb", 0) + wash_dumb
            output_by_room[3]["washed_smart"] += wash_smart
            output_by_room[3]["washed_dumb"] += wash_dumb

        if brewery:
            substrate = max(
                0,
                _stochastic_round(
                    brewery.output_wu * self._config.economy.substrate_gal_per_wu,
                    self._seed,
                    "substrate",
                    day,
                ),
            )
            inv["substrate_gallons"] = inv.get("substrate_gallons", 0) + substrate
            output_by_room[4]["substrate_gallons"] += substrate

        if weaving:
            ribbon = max(
                0,
                _stochastic_round(
                    weaving.output_wu * self._config.economy.ribbon_yards_per_wu,
                    self._seed,
                    "ribbon",
                    day,
                ),
            )
            inv["ribbon_yards"] = inv.get("ribbon_yards", 0) + ribbon
            output_by_room[5]["ribbon_yards"] += ribbon

        for rr in runtime_rooms.values():
            rr.output_today = dict(output_by_room.get(rr.room_id, _resource_zeroes()))

        return InventoryState(cash=start.inventory.cash, inventories=inv), output_by_room

    def _compute_perceived_progress(self, *, runtime_rooms: Mapping[int, PipelineRoomRuntime]) -> None:
        for rr in runtime_rooms.values():
            if rr.room_id in (1, 6):
                rr.progress_p = 0.0
                continue
            base_rate = max(0.1, float(self._config.base_rate_wu_by_room.get(rr.room_id, 1.0)))
            rr.progress_p = _clamp01((rr.output_wu / base_rate) - rr.fiasco_severity * 0.2)

    def _compute_relief(self, *, runtime_rooms: Mapping[int, PipelineRoomRuntime]) -> None:
        event_relief = self._loaded_config.raw.get("lookup_tables", {}).get("event_relief", {})
        relief_total_success = float(event_relief.get("total_success", 0.1))
        relief_accident_free = float(event_relief.get("accident_free", 0.05))

        for rr in runtime_rooms.values():
            if rr.room_id in (1, 6):
                rr.relief_total = 0.0
                continue
            rr.relief_event = 0.0
            if rr.outcome_label == "total_success":
                rr.relief_event += relief_total_success
            if rr.accidents_count == 0:
                rr.relief_event += relief_accident_free
            rr.relief_total = _clamp01(rr.relief_sup + rr.relief_event)

    def _update_worker_states(self, *, runtime_rooms: Mapping[int, PipelineRoomRuntime], regime: RegimeState) -> None:
        for rr in runtime_rooms.values():
            if rr.room_id in (1, 6):
                continue
            present_total = max(1, rr.present_dumb + rr.present_smart)
            rr.casualty_rate = rr.casualties / present_total
            h = rr.hours_effective / 9.0
            coeff = self._config.worker_equations
            s_old = rr.stress_old

            s_new = _clamp01(
                s_old
                + coeff.alpha_h * (h - 1.0)
                + coeff.alpha_f * rr.fiasco_severity
                + coeff.alpha_k * rr.casualty_rate
                - coeff.alpha_r * rr.relief_total
                - coeff.alpha_p * rr.progress_p
            )
            d_new = _clamp01(
                rr.discipline_old
                + coeff.beta_l * rr.l_value
                + coeff.beta_p * rr.progress_p
                - coeff.beta_s * s_old
                - coeff.beta_f * rr.fiasco_severity
            )

            indoctrination_term = coeff.gamma_i * rr.i_value
            if regime.inversion_days > 0:
                indoctrination_term *= -1.0

            a_new = _clamp01(
                rr.alignment_old
                + coeff.gamma_p * rr.progress_p
                + indoctrination_term
                - coeff.gamma_k * rr.casualty_rate
                - coeff.gamma_s * s_old
            )

            rr.stress_old = s_new
            rr.discipline_old = d_new
            rr.alignment_old = a_new

    def _update_supervisors(
        self,
        start: SimSimState,
        *,
        assignments: Mapping[str, int | None],
        outcomes: Mapping[str, str],
        conflict_resolution: Mapping[str, Any],
        factory_deltas: MutableMapping[str, float],
        emit: Any,
    ) -> Dict[str, SupervisorState]:
        out: Dict[str, SupervisorState] = {}
        supervisor_deltas = conflict_resolution.get("supervisor_deltas", {})

        for profile in SUPERVISOR_PROFILES:
            if not self._is_supervisor_unlocked(profile.code, start.day_tick + 1):
                continue
            prev = start.supervisors.get(profile.code)
            assigned_room = assignments.get(profile.code)
            if prev is None:
                prev = SupervisorState(
                    code=profile.code,
                    name=profile.name,
                    unlocked_day=self._supervisor_unlock_day(profile.code),
                    native_room=profile.native_room,
                    assigned_room=assigned_room,
                    loyalty=0.55,
                    confidence=0.5,
                    influence=0.5,
                    cooldown_days=0,
                )

            outcome = outcomes.get(profile.code, "neutral")
            delta_conf = float(self._config.confidence.outcome_delta.get(outcome, 0.0))
            delta_loyalty = 0.0
            delta_influence = 0.0

            if assigned_room == profile.native_room:
                delta_conf += self._config.confidence.native_bonus
            hated_rooms = set(self._loaded_config.raw.get("confidence", {}).get("hated_rooms", {}).get(profile.code, []))
            if isinstance(assigned_room, int) and assigned_room in hated_rooms:
                delta_conf += self._config.confidence.hated_penalty

            if assigned_room is None:
                delta_conf += self._config.confidence.unassigned_penalty
            elif assigned_room != profile.native_room and outcome in ("neutral", "small_fiasco", "total_fiasco"):
                delta_conf += self._config.confidence.non_native_no_success_penalty

            if prev.confidence < self._config.confidence.threshold_tension:
                delta_conf += self._config.confidence.base_drift_below_tension

            in_tension_zone = prev.confidence >= self._config.confidence.threshold_tension and prev.cooldown_days == 0
            if in_tension_zone:
                delta_conf *= self._config.confidence.tension_multiplier

            ext_delta = supervisor_deltas.get(profile.code, {})
            delta_conf += float(ext_delta.get("confidence", 0.0))
            delta_loyalty += float(ext_delta.get("loyalty", 0.0))
            delta_influence += float(ext_delta.get("influence", 0.0))

            new_conf = _clamp01(prev.confidence + delta_conf)
            new_loyalty = _clamp01(prev.loyalty + delta_loyalty)
            new_influence = _clamp01(prev.influence + delta_influence + (new_conf - prev.confidence) * 0.2)

            if in_tension_zone:
                passives = self._loaded_config.raw.get("confidence", {}).get("tension_passives", {}).get(profile.code, {})
                factory_deltas["stress"] += float(passives.get("stress", 0.0))
                factory_deltas["discipline"] += float(passives.get("discipline", 0.0))
                factory_deltas["alignment"] += float(passives.get("alignment", 0.0))
                factory_deltas["global_accident_bonus"] += float(passives.get("global_accident_bonus", 0.0))
                if "equipment_damage_multiplier" in passives:
                    factory_deltas["equipment_damage_multiplier"] *= float(passives.get("equipment_damage_multiplier", 1.0))
                emit("tension_zone", supervisor=profile.code, details={"confidence": round(new_conf, 3)})

            out[profile.code] = SupervisorState(
                code=profile.code,
                name=profile.name,
                unlocked_day=self._supervisor_unlock_day(profile.code),
                native_room=profile.native_room,
                assigned_room=assigned_room,
                loyalty=new_loyalty,
                confidence=new_conf,
                influence=new_influence,
                cooldown_days=max(0, int(prev.cooldown_days)),
            )

        return out

    def _handle_critical_events(
        self,
        *,
        day: int,
        supervisors: Dict[str, SupervisorState],
        assignments: Mapping[str, int | None],
        day_input: DayInput,
        regime: RegimeState,
        hidden: HiddenAccumulatorState,
        prompts: List[PromptState],
        emit: Any,
    ) -> Dict[str, Any]:
        if day < self._config.guardrails.prevent_critical_before_day:
            return {"supervisors": supervisors, "regime": regime, "hidden": hidden}

        candidates: List[SupervisorState] = []
        for sup in supervisors.values():
            if sup.cooldown_days > 0:
                continue
            if sup.confidence < self._config.confidence.threshold_critical:
                continue
            if sup.assigned_room != sup.native_room:
                continue
            candidates.append(sup)

        if not candidates:
            return {"supervisors": supervisors, "regime": regime, "hidden": hidden}

        chosen = sorted(candidates, key=lambda s: (-s.confidence, s.code))[0]
        prompt_id = f"prompt_critical_{day}_{chosen.code}"
        choices = ("allow", "suppress")
        responses = {r.prompt_id: r.choice for r in day_input.prompt_responses}
        selected = responses.get(prompt_id)
        if selected not in choices:
            selected = "allow"

        prompts.append(
            PromptState(
                prompt_id=prompt_id,
                kind="critical",
                tick=day,
                choices=choices,
                status="resolved",
                selected_choice=selected,
                payload={"supervisor": chosen.code, "room_id": chosen.assigned_room},
            )
        )

        if selected == "suppress":
            sup = supervisors[chosen.code]
            supervisors[chosen.code] = SupervisorState(
                code=sup.code,
                name=sup.name,
                unlocked_day=sup.unlocked_day,
                native_room=sup.native_room,
                assigned_room=sup.assigned_room,
                loyalty=_clamp01(sup.loyalty + self._config.confidence.suppress_loyalty_penalty),
                confidence=_clamp01(sup.confidence + self._config.confidence.suppress_confidence_penalty),
                influence=_clamp01(sup.influence + self._config.confidence.suppress_influence_penalty),
                cooldown_days=sup.cooldown_days,
            )
            emit("critical_suppressed", supervisor=chosen.code)
            return {"supervisors": supervisors, "regime": regime, "hidden": hidden}

        event_cfg = self._config.critical_events.get(chosen.code, {})
        emit("critical_triggered", supervisor=chosen.code, details={"name": event_cfg.get("name", chosen.code)})

        # Apply core effects.
        next_regime = regime
        next_hidden = HiddenAccumulatorState(
            rigidity=hidden.rigidity,
            radical_potential=hidden.radical_potential,
            innovation_pressure=hidden.innovation_pressure,
        )

        if chosen.code == "W":
            next_regime = RegimeState(
                refactor_days=int(event_cfg.get("duration_days", 3)),
                inversion_days=regime.inversion_days,
                shutdown_except_brewery_today=bool(event_cfg.get("shutdown_except_brewery_today", True)),
                weaving_boost_next_day=regime.weaving_boost_next_day,
                weaving_boost_multiplier_today=regime.weaving_boost_multiplier_today,
                global_accident_bonus=regime.global_accident_bonus,
                pending_accident_bonus_next_day=max(
                    regime.pending_accident_bonus_next_day,
                    float(event_cfg.get("next_day_accident_bonus_if_low_discipline", 0.15)),
                ),
                global_non_weaving_output_multiplier_today=regime.global_non_weaving_output_multiplier_today,
                lockdown_today=regime.lockdown_today,
            )
            next_hidden = HiddenAccumulatorState(
                rigidity=hidden.rigidity + float(event_cfg.get("rigidity_delta", 0.0)),
                radical_potential=hidden.radical_potential + float(event_cfg.get("radical_potential_delta", 0.0)),
                innovation_pressure=hidden.innovation_pressure + float(event_cfg.get("innovation_pressure_delta", 0.0)),
            )
            if "C" in supervisors:
                c = supervisors["C"]
                supervisors["C"] = SupervisorState(
                    code=c.code,
                    name=c.name,
                    unlocked_day=c.unlocked_day,
                    native_room=c.native_room,
                    assigned_room=c.assigned_room,
                    loyalty=c.loyalty,
                    confidence=_clamp01(c.confidence + float(event_cfg.get("cathexis_confidence_delta", 0.2))),
                    influence=c.influence,
                    cooldown_days=c.cooldown_days,
                )
        elif chosen.code == "T":
            next_regime = RegimeState(
                refactor_days=regime.refactor_days,
                inversion_days=int(event_cfg.get("duration_days", 2)),
                shutdown_except_brewery_today=regime.shutdown_except_brewery_today,
                weaving_boost_next_day=regime.weaving_boost_next_day,
                weaving_boost_multiplier_today=regime.weaving_boost_multiplier_today,
                global_accident_bonus=max(regime.global_accident_bonus, float(event_cfg.get("global_accident_bonus", 0.05))),
                pending_accident_bonus_next_day=regime.pending_accident_bonus_next_day,
                global_non_weaving_output_multiplier_today=float(
                    event_cfg.get("global_non_weaving_output_multiplier_today", event_cfg.get("global_non_weaving_output_multiplier", 0.5))
                ),
                lockdown_today=regime.lockdown_today,
            )
            next_hidden = HiddenAccumulatorState(
                rigidity=hidden.rigidity + float(event_cfg.get("rigidity_delta", 0.0)),
                radical_potential=hidden.radical_potential + float(event_cfg.get("radical_potential_delta", 0.0)),
                innovation_pressure=hidden.innovation_pressure + float(event_cfg.get("innovation_pressure_delta", 0.0)),
            )
            if "C" in supervisors:
                c = supervisors["C"]
                supervisors["C"] = SupervisorState(
                    code=c.code,
                    name=c.name,
                    unlocked_day=c.unlocked_day,
                    native_room=c.native_room,
                    assigned_room=c.assigned_room,
                    loyalty=c.loyalty,
                    confidence=c.confidence,
                    influence=_clamp01(c.influence + float(event_cfg.get("cathexis_influence_delta", 0.2))),
                    cooldown_days=c.cooldown_days,
                )
            if "L" in supervisors:
                l = supervisors["L"]
                supervisors["L"] = SupervisorState(
                    code=l.code,
                    name=l.name,
                    unlocked_day=l.unlocked_day,
                    native_room=l.native_room,
                    assigned_room=l.assigned_room,
                    loyalty=_clamp01(l.loyalty + float(event_cfg.get("limen_loyalty_delta", -0.15))),
                    confidence=l.confidence,
                    influence=l.influence,
                    cooldown_days=l.cooldown_days,
                )
        elif chosen.code == "L":
            next_regime = RegimeState(
                refactor_days=regime.refactor_days,
                inversion_days=regime.inversion_days,
                shutdown_except_brewery_today=regime.shutdown_except_brewery_today,
                weaving_boost_next_day=regime.weaving_boost_next_day,
                weaving_boost_multiplier_today=regime.weaving_boost_multiplier_today,
                global_accident_bonus=regime.global_accident_bonus,
                pending_accident_bonus_next_day=regime.pending_accident_bonus_next_day,
                global_non_weaving_output_multiplier_today=float(event_cfg.get("factory_output_multiplier_today", 0.0)),
                lockdown_today=True,
            )
        elif chosen.code == "S":
            next_regime = RegimeState(
                refactor_days=regime.refactor_days,
                inversion_days=regime.inversion_days,
                shutdown_except_brewery_today=regime.shutdown_except_brewery_today,
                weaving_boost_next_day=regime.weaving_boost_next_day,
                weaving_boost_multiplier_today=regime.weaving_boost_multiplier_today,
                global_accident_bonus=regime.global_accident_bonus,
                pending_accident_bonus_next_day=regime.pending_accident_bonus_next_day,
                global_non_weaving_output_multiplier_today=regime.global_non_weaving_output_multiplier_today,
                lockdown_today=regime.lockdown_today,
            )
        elif chosen.code == "C":
            next_regime = regime

        reset_conf = float(event_cfg.get("reset_confidence", 0.55))
        reset_cd = int(event_cfg.get("cooldown_days", self._config.confidence.cooldown_days_on_critical))
        sup = supervisors[chosen.code]
        supervisors[chosen.code] = SupervisorState(
            code=sup.code,
            name=sup.name,
            unlocked_day=sup.unlocked_day,
            native_room=sup.native_room,
            assigned_room=sup.assigned_room,
            loyalty=sup.loyalty,
            confidence=_clamp01(reset_conf),
            influence=sup.influence,
            cooldown_days=max(0, reset_cd),
        )

        return {"supervisors": supervisors, "regime": next_regime, "hidden": next_hidden}

    def _apply_end_of_day_actions(
        self,
        *,
        inventory: InventoryState,
        worker_pools: WorkerPoolState,
        actions: EndOfDayActions,
        day: int,
        emit: Any,
    ) -> tuple[InventoryState, WorkerPoolState]:
        inv = dict(inventory.inventories)
        cash = int(inventory.cash)

        # Upgrades first.
        max_upgrade = min(
            int(actions.upgrade_brains),
            inv.get("washed_dumb", 0),
            inv.get("substrate_gallons", 0),
            inv.get("ribbon_yards", 0),
        )
        if max_upgrade > 0:
            inv["washed_dumb"] -= max_upgrade
            inv["washed_smart"] = inv.get("washed_smart", 0) + max_upgrade
            inv["substrate_gallons"] -= max_upgrade
            inv["ribbon_yards"] -= max_upgrade
            emit("eod_upgrade", details={"count": max_upgrade})

        # Selling.
        sell_dumb = min(int(actions.sell_washed_dumb), inv.get("washed_dumb", 0))
        sell_smart = min(int(actions.sell_washed_smart), inv.get("washed_smart", 0))
        if sell_dumb > 0 or sell_smart > 0:
            inv["washed_dumb"] -= sell_dumb
            inv["washed_smart"] -= sell_smart
            cash += sell_dumb * self._config.economy.sell_washed_dumb
            cash += sell_smart * self._config.economy.sell_washed_smart
            emit("eod_sell", details={"washed_dumb": sell_dumb, "washed_smart": sell_smart})

        # Conversions.
        convert_cost = int(self._config.economy.convert_cost)
        conv_dumb = min(int(actions.convert_workers_dumb), inv.get("washed_dumb", 0) // convert_cost)
        conv_smart = min(int(actions.convert_workers_smart), inv.get("washed_smart", 0) // convert_cost)
        if conv_dumb > 0 or conv_smart > 0:
            inv["washed_dumb"] -= conv_dumb * convert_cost
            inv["washed_smart"] -= conv_smart * convert_cost
            worker_pools = WorkerPoolState(
                dumb_total=worker_pools.dumb_total + conv_dumb,
                smart_total=worker_pools.smart_total + conv_smart,
            )
            emit("eod_convert", details={"dumb": conv_dumb, "smart": conv_smart})

        return InventoryState(cash=cash, inventories=inv), worker_pools

    def _update_hidden_accumulators(
        self,
        *,
        hidden: HiddenAccumulatorState,
        runtime_rooms: Mapping[int, PipelineRoomRuntime],
        security_lead: str,
        output_by_room: Mapping[int, Mapping[str, int]],
        upgrade_count: int,
        casualties: int,
    ) -> HiddenAccumulatorState:
        discipline_avg = 0.0
        alignment_avg = 0.0
        total_present = 0
        for rr in runtime_rooms.values():
            if rr.room_id in (1, 6):
                continue
            present = rr.present_dumb + rr.present_smart
            if present <= 0:
                continue
            discipline_avg += present * rr.discipline_old
            alignment_avg += present * rr.alignment_old
            total_present += present
        if total_present > 0:
            discipline_avg /= total_present
            alignment_avg /= total_present

        output_total = 0
        for room_out in output_by_room.values():
            output_total += sum(int(v) for v in room_out.values())

        rigidity = hidden.rigidity
        if security_lead == "L":
            rigidity += self._config.hidden_accumulators.rigidity_limen_security
        rigidity += discipline_avg * self._config.hidden_accumulators.rigidity_discipline

        radical = hidden.radical_potential
        radical += (1.0 - alignment_avg) * self._config.hidden_accumulators.radical_from_low_alignment
        radical += float(casualties) * self._config.hidden_accumulators.radical_from_casualties

        innovation = hidden.innovation_pressure
        innovation += output_total * self._config.hidden_accumulators.innovation_from_output
        innovation += float(max(0, upgrade_count)) * self._config.hidden_accumulators.innovation_from_upgrades

        return HiddenAccumulatorState(
            rigidity=max(0.0, rigidity),
            radical_potential=max(0.0, radical),
            innovation_pressure=max(0.0, innovation),
        )

    def _finalize_rooms(
        self,
        *,
        day: int,
        assignments: Mapping[str, int | None],
        runtime_rooms: Mapping[int, PipelineRoomRuntime],
        output_by_room: Mapping[int, Mapping[str, int]],
        supervisors: Mapping[str, SupervisorState],
        previous: Mapping[int, RoomState],
    ) -> Dict[int, RoomState]:
        supervisor_by_room: Dict[int, str] = {}
        for code, room in assignments.items():
            if isinstance(room, int):
                supervisor_by_room[room] = code

        rooms: Dict[int, RoomState] = {}
        for room_id in ROOM_IDS:
            unlocked_day = self._room_unlock_day(room_id)
            locked = not self._is_room_unlocked(room_id, day)

            if room_id == 1:
                rooms[1] = RoomState(
                    room_id=1,
                    name=ROOM_NAMES[1],
                    unlocked_day=0,
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

            if room_id == 6 or locked:
                rooms[room_id] = RoomState(
                    room_id=room_id,
                    name=ROOM_NAMES[room_id],
                    unlocked_day=unlocked_day,
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

            rr = runtime_rooms.get(room_id)
            if rr is None:
                prev = previous[room_id]
                rooms[room_id] = prev
                continue

            rooms[room_id] = RoomState(
                room_id=room_id,
                name=ROOM_NAMES[room_id],
                unlocked_day=unlocked_day,
                locked=False,
                supervisor=supervisor_by_room.get(room_id),
                workers_assigned_dumb=rr.assigned_dumb,
                workers_assigned_smart=rr.assigned_smart,
                workers_present_dumb=rr.present_dumb,
                workers_present_smart=rr.present_smart,
                equipment_condition=_clamp01(rr.equipment_after_damage),
                stress=_clamp01(rr.stress_old),
                discipline=_clamp01(rr.discipline_old),
                alignment=_clamp01(rr.alignment_old),
                output_today=dict(output_by_room.get(room_id, _resource_zeroes())),
                accidents_count=int(rr.accidents_count),
                casualties=int(rr.casualties),
            )

        return rooms


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
        f"config_id={state.config_id} config_hash={state.config_hash[:12]}",
        (
            "workers="
            f"{state.worker_pools.dumb_total}d/{state.worker_pools.smart_total}s "
            f"regime(refactor={state.regime.refactor_days}, inversion={state.regime.inversion_days}, "
            f"shutdown={state.regime.shutdown_except_brewery_today})"
        ),
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
            lines.append("  room1 Security: lead=L (no workers/output)")
            continue
        lines.append(
            f"  room {room.room_id} {room.name}: sup={room.supervisor or '-'} "
            f"assigned={room.workers_assigned_dumb}/{room.workers_assigned_smart} "
            f"present={room.workers_present_dumb}/{room.workers_present_smart} "
            f"equip={room.equipment_condition:.2f} stress={room.stress:.2f} disc={room.discipline:.2f} "
            f"align={room.alignment:.2f} casualties={room.casualties}"
        )

    if state.prompts:
        lines.append("prompts:")
        for prompt in state.prompts[-5:]:
            lines.append(
                f"  t{prompt.tick} {prompt.prompt_id} kind={prompt.kind} choice={prompt.selected_choice}"
            )

    if state.events:
        lines.append("events:")
        for ev in state.events[-8:]:
            lines.append(
                f"  t={ev.get('tick')} id={ev.get('event_id')} kind={ev.get('kind')} "
                f"room={ev.get('room_id')} sup={ev.get('supervisor')}"
            )

    return "\n".join(lines)
