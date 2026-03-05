from __future__ import annotations

"""Typed config model + validation for sim_sim_1."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, Mapping, Sequence, Tuple


SCHEMA_DOC_PATH = "docs/sim_sim/sim_sim_1_config_schema.md"


class ConfigValidationError(ValueError):
    """Raised when sim_sim config is missing required fields."""


@dataclass(frozen=True)
class WorkerEquationCoefficients:
    alpha_h: float
    alpha_f: float
    alpha_k: float
    alpha_r: float
    alpha_p: float
    beta_l: float
    beta_p: float
    beta_s: float
    beta_f: float
    gamma_p: float
    gamma_i: float
    gamma_k: float
    gamma_s: float


@dataclass(frozen=True)
class AbsenteeismFormula:
    base: float
    stress_coeff: float
    discipline_coeff: float


@dataclass(frozen=True)
class AccidentFormula:
    base: float
    low_discipline_coeff: float
    high_stress_coeff: float
    low_equipment_coeff: float


@dataclass(frozen=True)
class ProductivityFormula:
    base: float
    discipline_coeff: float
    stress_coeff: float
    refactor_base: float
    refactor_discipline_coeff: float
    refactor_stress_coeff: float


@dataclass(frozen=True)
class RoomCapacity:
    max_dumb: int
    max_smart: int
    max_total: int
    no_workers: bool = False


@dataclass(frozen=True)
class EconomyConfig:
    brains_per_wu: int
    wash_capacity_per_wu: int
    substrate_gal_per_wu: int
    ribbon_yards_per_wu: int
    sell_washed_dumb: int
    sell_washed_smart: int
    convert_cost: int


@dataclass(frozen=True)
class LookupTables:
    default_l: float
    default_i: float
    default_relief: float
    leadership_order: Mapping[str, Mapping[int, float]]
    indoctrination_pressure: Mapping[str, Mapping[int, float]]
    relief_baseline: Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class SecurityConfig:
    thrum_failure_chance: float
    c_or_t_absent_bonus_base: float
    c_or_t_absent_bonus_scale: float
    thrum_failure_extra_absent_flat: float
    random_keep_bias_cathexis: float
    random_keep_bias_thrum_success: float
    stiletto_pull_order: Tuple[int, ...]
    witch_pull_order: Tuple[int, ...]


@dataclass(frozen=True)
class ConflictConfig:
    hostile_pairs: Tuple[Tuple[str, str], ...]
    discovered_discipline_delta: float
    discovered_loyalty_delta: float
    support_confidence_delta: float
    oppose_confidence_delta: float
    support_influence_delta: float
    oppose_influence_delta: float
    support_loyalty_delta: float
    oppose_loyalty_delta: float
    security_edge_priority: int
    edge_priority: Mapping[str, int]
    ideology_shift: float


@dataclass(frozen=True)
class ConfidenceConfig:
    threshold_tension: float
    threshold_critical: float
    cooldown_days_on_critical: int
    base_drift_below_tension: float
    tension_multiplier: float
    native_bonus: float
    hated_penalty: float
    unassigned_penalty: float
    non_native_no_success_penalty: float
    suppress_confidence_penalty: float
    suppress_loyalty_penalty: float
    suppress_influence_penalty: float
    suppress_factory_stress_delta: float
    outcome_delta: Mapping[str, float]


@dataclass(frozen=True)
class InitialStateConfig:
    cash: int
    worker_dumb: int
    worker_smart: int
    inventory: Mapping[str, int]
    initial_equipment_condition: float
    initial_stress_min: float
    initial_stress_max: float
    initial_discipline: float
    initial_alignment: float


@dataclass(frozen=True)
class HiddenAccumulatorConfig:
    rigidity_limen_security: float
    rigidity_discipline: float
    radical_from_low_alignment: float
    radical_from_casualties: float
    innovation_from_output: float
    innovation_from_upgrades: float


@dataclass(frozen=True)
class GuardrailConfig:
    early_days_max_casualties: int
    early_days_casualty_cap_until_day: int
    prevent_critical_before_day: int


@dataclass(frozen=True)
class SimSimConfig:
    metadata: Mapping[str, Any]
    worker_equations: WorkerEquationCoefficients
    absenteeism: AbsenteeismFormula
    accident: AccidentFormula
    productivity: ProductivityFormula
    base_rate_wu_by_room: Mapping[int, float]
    room_capacities: Mapping[int, RoomCapacity]
    economy: EconomyConfig
    lookup_tables: LookupTables
    security: SecurityConfig
    conflicts: ConflictConfig
    confidence: ConfidenceConfig
    critical_events: Mapping[str, Mapping[str, Any]]
    outcome_tables: Mapping[str, Mapping[int, Tuple[Mapping[str, Any], ...]]]
    initial_state: InitialStateConfig
    unlock_schedule_rooms: Mapping[int, int]
    unlock_schedule_supervisors: Mapping[str, int]
    hidden_accumulators: HiddenAccumulatorConfig
    guardrails: GuardrailConfig


def _fail(path: str, message: str) -> ConfigValidationError:
    return ConfigValidationError(f"sim_sim config invalid at '{path}': {message}. See {SCHEMA_DOC_PATH}")


def _require_mapping(root: Mapping[str, Any], key: str, *, path: str) -> Mapping[str, Any]:
    value = root.get(key)
    if not isinstance(value, Mapping):
        raise _fail(f"{path}.{key}", "expected object")
    return value


def _require_number(root: Mapping[str, Any], key: str, *, path: str) -> float:
    value = root.get(key)
    if not isinstance(value, (int, float)):
        raise _fail(f"{path}.{key}", "expected number")
    return float(value)


def _require_int(root: Mapping[str, Any], key: str, *, path: str) -> int:
    value = root.get(key)
    if not isinstance(value, int):
        raise _fail(f"{path}.{key}", "expected integer")
    return int(value)


def _require_bool(root: Mapping[str, Any], key: str, *, path: str) -> bool:
    value = root.get(key)
    if not isinstance(value, bool):
        raise _fail(f"{path}.{key}", "expected boolean")
    return bool(value)


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    frozen: Dict[str, Any] = {}
    for k, v in value.items():
        if isinstance(v, Mapping):
            frozen[str(k)] = _freeze_mapping(v)
        elif isinstance(v, list):
            frozen[str(k)] = tuple(v)
        else:
            frozen[str(k)] = v
    return MappingProxyType(frozen)


def _parse_lookup_table(
    section: Mapping[str, Any],
    key: str,
    *,
    path: str,
) -> Mapping[str, Mapping[int, float]]:
    raw = _require_mapping(section, key, path=path)
    out: Dict[str, Mapping[int, float]] = {}
    for sup, raw_by_room in raw.items():
        if not isinstance(raw_by_room, Mapping):
            raise _fail(f"{path}.{key}.{sup}", "expected object")
        room_map: Dict[int, float] = {}
        for room_id, value in raw_by_room.items():
            if not isinstance(value, (int, float)):
                raise _fail(f"{path}.{key}.{sup}.{room_id}", "expected number")
            room_map[int(room_id)] = float(value)
        out[str(sup)] = MappingProxyType(room_map)
    return MappingProxyType(out)


def _parse_relief_table(section: Mapping[str, Any], *, path: str) -> Mapping[str, Mapping[str, float]]:
    raw = _require_mapping(section, "relief_baseline", path=path)
    out: Dict[str, Mapping[str, float]] = {}
    for sup, values in raw.items():
        if not isinstance(values, Mapping):
            raise _fail(f"{path}.relief_baseline.{sup}", "expected object")
        row: Dict[str, float] = {}
        for k, v in values.items():
            if not isinstance(v, (int, float)):
                raise _fail(f"{path}.relief_baseline.{sup}.{k}", "expected number")
            row[str(k)] = float(v)
        out[str(sup)] = MappingProxyType(row)
    return MappingProxyType(out)


def _parse_room_capacities(section: Mapping[str, Any]) -> Mapping[int, RoomCapacity]:
    out: Dict[int, RoomCapacity] = {}
    for room_id, raw in section.items():
        if not isinstance(raw, Mapping):
            raise _fail(f"room_capacities.{room_id}", "expected object")
        out[int(room_id)] = RoomCapacity(
            max_dumb=int(raw.get("max_dumb", 0)),
            max_smart=int(raw.get("max_smart", 0)),
            max_total=int(raw.get("max_total", 0)),
            no_workers=bool(raw.get("no_workers", False)),
        )
    return MappingProxyType(out)


def _parse_float_room_map(section: Mapping[str, Any], *, path: str) -> Mapping[int, float]:
    out: Dict[int, float] = {}
    for room_id, value in section.items():
        if not isinstance(value, (int, float)):
            raise _fail(f"{path}.{room_id}", "expected number")
        out[int(room_id)] = float(value)
    return MappingProxyType(out)


def _parse_hostile_pairs(raw_pairs: Any) -> Tuple[Tuple[str, str], ...]:
    if not isinstance(raw_pairs, Sequence):
        raise _fail("conflicts.hostile_pairs", "expected array")
    pairs: list[Tuple[str, str]] = []
    for i, raw in enumerate(raw_pairs):
        if not (isinstance(raw, Sequence) and len(raw) == 2):
            raise _fail(f"conflicts.hostile_pairs[{i}]", "expected 2-item array")
        a, b = str(raw[0]), str(raw[1])
        pairs.append((a, b))
    return tuple(pairs)


def _parse_outcome_tables(raw: Mapping[str, Any]) -> Mapping[str, Mapping[int, Tuple[Mapping[str, Any], ...]]]:
    out: Dict[str, Mapping[int, Tuple[Mapping[str, Any], ...]]] = {}
    for sup, by_room in raw.items():
        if not isinstance(by_room, Mapping):
            raise _fail(f"outcome_tables.{sup}", "expected object")
        sup_rows: Dict[int, Tuple[Mapping[str, Any], ...]] = {}
        for room_id, outcomes in by_room.items():
            if not isinstance(outcomes, Sequence):
                raise _fail(f"outcome_tables.{sup}.{room_id}", "expected array")
            rows: list[Mapping[str, Any]] = []
            for idx, row in enumerate(outcomes):
                if not isinstance(row, Mapping):
                    raise _fail(f"outcome_tables.{sup}.{room_id}[{idx}]", "expected object")
                if not isinstance(row.get("weight"), (int, float)):
                    raise _fail(f"outcome_tables.{sup}.{room_id}[{idx}].weight", "expected number")
                rows.append(_freeze_mapping(row))
            sup_rows[int(room_id)] = tuple(rows)
        out[str(sup)] = MappingProxyType(sup_rows)
    return MappingProxyType(out)


def parse_sim_sim_config(raw: Mapping[str, Any]) -> SimSimConfig:
    if not isinstance(raw, Mapping):
        raise _fail("$", "top-level value must be an object")

    metadata = _require_mapping(raw, "metadata", path="$")
    formulas = _require_mapping(raw, "formulas", path="$")
    base_rate_wu_by_room_raw = _require_mapping(raw, "base_rate_wu_by_room", path="$")
    worker = _require_mapping(raw, "worker_equations", path="$")
    room_caps_raw = _require_mapping(raw, "room_capacities", path="$")
    economy_raw = _require_mapping(raw, "economy", path="$")
    lookup_raw = _require_mapping(raw, "lookup_tables", path="$")
    security_raw = _require_mapping(raw, "security", path="$")
    conflicts_raw = _require_mapping(raw, "conflicts", path="$")
    confidence_raw = _require_mapping(raw, "confidence", path="$")
    critical_raw = _require_mapping(raw, "critical_events", path="$")
    outcome_raw = _require_mapping(raw, "outcome_tables", path="$")
    initial_raw = _require_mapping(raw, "initial_state", path="$")
    unlock_raw = _require_mapping(raw, "unlock_schedule", path="$")
    hidden_raw = _require_mapping(raw, "hidden_accumulators", path="$")
    guardrails_raw = _require_mapping(raw, "guardrails", path="$")

    absenteeism_raw = _require_mapping(formulas, "absenteeism", path="$.formulas")
    accident_raw = _require_mapping(formulas, "accident", path="$.formulas")
    productivity_raw = _require_mapping(formulas, "productivity", path="$.formulas")

    worker_equations = WorkerEquationCoefficients(
        alpha_h=_require_number(worker, "alpha_h", path="$.worker_equations"),
        alpha_f=_require_number(worker, "alpha_f", path="$.worker_equations"),
        alpha_k=_require_number(worker, "alpha_k", path="$.worker_equations"),
        alpha_r=_require_number(worker, "alpha_r", path="$.worker_equations"),
        alpha_p=_require_number(worker, "alpha_p", path="$.worker_equations"),
        beta_l=_require_number(worker, "beta_l", path="$.worker_equations"),
        beta_p=_require_number(worker, "beta_p", path="$.worker_equations"),
        beta_s=_require_number(worker, "beta_s", path="$.worker_equations"),
        beta_f=_require_number(worker, "beta_f", path="$.worker_equations"),
        gamma_p=_require_number(worker, "gamma_p", path="$.worker_equations"),
        gamma_i=_require_number(worker, "gamma_i", path="$.worker_equations"),
        gamma_k=_require_number(worker, "gamma_k", path="$.worker_equations"),
        gamma_s=_require_number(worker, "gamma_s", path="$.worker_equations"),
    )

    absenteeism = AbsenteeismFormula(
        base=_require_number(absenteeism_raw, "base", path="$.formulas.absenteeism"),
        stress_coeff=_require_number(absenteeism_raw, "stress_coeff", path="$.formulas.absenteeism"),
        discipline_coeff=_require_number(absenteeism_raw, "discipline_coeff", path="$.formulas.absenteeism"),
    )
    accident = AccidentFormula(
        base=_require_number(accident_raw, "base", path="$.formulas.accident"),
        low_discipline_coeff=_require_number(
            accident_raw, "low_discipline_coeff", path="$.formulas.accident"
        ),
        high_stress_coeff=_require_number(accident_raw, "high_stress_coeff", path="$.formulas.accident"),
        low_equipment_coeff=_require_number(
            accident_raw, "low_equipment_coeff", path="$.formulas.accident"
        ),
    )
    productivity = ProductivityFormula(
        base=_require_number(productivity_raw, "base", path="$.formulas.productivity"),
        discipline_coeff=_require_number(
            productivity_raw, "discipline_coeff", path="$.formulas.productivity"
        ),
        stress_coeff=_require_number(productivity_raw, "stress_coeff", path="$.formulas.productivity"),
        refactor_base=_require_number(productivity_raw, "refactor_base", path="$.formulas.productivity"),
        refactor_discipline_coeff=_require_number(
            productivity_raw, "refactor_discipline_coeff", path="$.formulas.productivity"
        ),
        refactor_stress_coeff=_require_number(
            productivity_raw, "refactor_stress_coeff", path="$.formulas.productivity"
        ),
    )

    lookup_tables = LookupTables(
        default_l=_require_number(lookup_raw, "default_l", path="$.lookup_tables"),
        default_i=_require_number(lookup_raw, "default_i", path="$.lookup_tables"),
        default_relief=_require_number(lookup_raw, "default_relief", path="$.lookup_tables"),
        leadership_order=_parse_lookup_table(lookup_raw, "leadership_order", path="$.lookup_tables"),
        indoctrination_pressure=_parse_lookup_table(lookup_raw, "indoctrination_pressure", path="$.lookup_tables"),
        relief_baseline=_parse_relief_table(lookup_raw, path="$.lookup_tables"),
    )

    security = SecurityConfig(
        thrum_failure_chance=_require_number(security_raw, "thrum_failure_chance", path="$.security"),
        c_or_t_absent_bonus_base=_require_number(
            security_raw, "c_or_t_absent_bonus_base", path="$.security"
        ),
        c_or_t_absent_bonus_scale=_require_number(
            security_raw, "c_or_t_absent_bonus_scale", path="$.security"
        ),
        thrum_failure_extra_absent_flat=_require_number(
            security_raw, "thrum_failure_extra_absent_flat", path="$.security"
        ),
        random_keep_bias_cathexis=_require_number(
            security_raw, "random_keep_bias_cathexis", path="$.security"
        ),
        random_keep_bias_thrum_success=_require_number(
            security_raw, "random_keep_bias_thrum_success", path="$.security"
        ),
        stiletto_pull_order=tuple(int(v) for v in security_raw.get("stiletto_pull_order", [5, 4, 3])),
        witch_pull_order=tuple(int(v) for v in security_raw.get("witch_pull_order", [3, 2])),
    )

    edge_priority_raw = _require_mapping(conflicts_raw, "edge_priority", path="$.conflicts")
    edge_priority: Dict[str, int] = {}
    for edge, value in edge_priority_raw.items():
        if not isinstance(value, int):
            raise _fail(f"$.conflicts.edge_priority.{edge}", "expected integer")
        edge_priority[str(edge)] = int(value)

    conflicts = ConflictConfig(
        hostile_pairs=_parse_hostile_pairs(conflicts_raw.get("hostile_pairs", [])),
        discovered_discipline_delta=_require_number(
            conflicts_raw, "discovered_discipline_delta", path="$.conflicts"
        ),
        discovered_loyalty_delta=_require_number(
            conflicts_raw, "discovered_loyalty_delta", path="$.conflicts"
        ),
        support_confidence_delta=_require_number(
            conflicts_raw, "support_confidence_delta", path="$.conflicts"
        ),
        oppose_confidence_delta=_require_number(conflicts_raw, "oppose_confidence_delta", path="$.conflicts"),
        support_influence_delta=_require_number(conflicts_raw, "support_influence_delta", path="$.conflicts"),
        oppose_influence_delta=_require_number(conflicts_raw, "oppose_influence_delta", path="$.conflicts"),
        support_loyalty_delta=_require_number(conflicts_raw, "support_loyalty_delta", path="$.conflicts"),
        oppose_loyalty_delta=_require_number(conflicts_raw, "oppose_loyalty_delta", path="$.conflicts"),
        security_edge_priority=_require_int(conflicts_raw, "security_edge_priority", path="$.conflicts"),
        edge_priority=MappingProxyType(edge_priority),
        ideology_shift=_require_number(conflicts_raw, "ideology_shift", path="$.conflicts"),
    )

    outcome_delta_raw = _require_mapping(confidence_raw, "outcome_delta", path="$.confidence")
    outcome_delta: Dict[str, float] = {}
    for outcome_key, value in outcome_delta_raw.items():
        if not isinstance(value, (int, float)):
            raise _fail(f"$.confidence.outcome_delta.{outcome_key}", "expected number")
        outcome_delta[str(outcome_key)] = float(value)

    confidence = ConfidenceConfig(
        threshold_tension=_require_number(confidence_raw, "threshold_tension", path="$.confidence"),
        threshold_critical=_require_number(confidence_raw, "threshold_critical", path="$.confidence"),
        cooldown_days_on_critical=_require_int(confidence_raw, "cooldown_days_on_critical", path="$.confidence"),
        base_drift_below_tension=_require_number(confidence_raw, "base_drift_below_tension", path="$.confidence"),
        tension_multiplier=_require_number(confidence_raw, "tension_multiplier", path="$.confidence"),
        native_bonus=_require_number(confidence_raw, "native_bonus", path="$.confidence"),
        hated_penalty=_require_number(confidence_raw, "hated_penalty", path="$.confidence"),
        unassigned_penalty=_require_number(confidence_raw, "unassigned_penalty", path="$.confidence"),
        non_native_no_success_penalty=_require_number(
            confidence_raw, "non_native_no_success_penalty", path="$.confidence"
        ),
        suppress_confidence_penalty=_require_number(
            confidence_raw, "suppress_confidence_penalty", path="$.confidence"
        ),
        suppress_loyalty_penalty=_require_number(confidence_raw, "suppress_loyalty_penalty", path="$.confidence"),
        suppress_influence_penalty=_require_number(
            confidence_raw, "suppress_influence_penalty", path="$.confidence"
        ),
        suppress_factory_stress_delta=_require_number(
            confidence_raw, "suppress_factory_stress_delta", path="$.confidence"
        ),
        outcome_delta=MappingProxyType(outcome_delta),
    )

    economy = EconomyConfig(
        brains_per_wu=_require_int(economy_raw, "brains_per_wu", path="$.economy"),
        wash_capacity_per_wu=_require_int(economy_raw, "wash_capacity_per_wu", path="$.economy"),
        substrate_gal_per_wu=_require_int(economy_raw, "substrate_gal_per_wu", path="$.economy"),
        ribbon_yards_per_wu=_require_int(economy_raw, "ribbon_yards_per_wu", path="$.economy"),
        sell_washed_dumb=_require_int(economy_raw, "sell_washed_dumb", path="$.economy"),
        sell_washed_smart=_require_int(economy_raw, "sell_washed_smart", path="$.economy"),
        convert_cost=_require_int(economy_raw, "convert_cost", path="$.economy"),
    )

    initial_inventory_raw = _require_mapping(initial_raw, "inventory", path="$.initial_state")
    initial_inventory: Dict[str, int] = {}
    for k, v in initial_inventory_raw.items():
        if not isinstance(v, int):
            raise _fail(f"$.initial_state.inventory.{k}", "expected integer")
        initial_inventory[str(k)] = int(v)

    initial_state = InitialStateConfig(
        cash=_require_int(initial_raw, "cash", path="$.initial_state"),
        worker_dumb=_require_int(initial_raw, "worker_dumb", path="$.initial_state"),
        worker_smart=_require_int(initial_raw, "worker_smart", path="$.initial_state"),
        inventory=MappingProxyType(initial_inventory),
        initial_equipment_condition=_require_number(
            initial_raw, "initial_equipment_condition", path="$.initial_state"
        ),
        initial_stress_min=_require_number(initial_raw, "initial_stress_min", path="$.initial_state"),
        initial_stress_max=_require_number(initial_raw, "initial_stress_max", path="$.initial_state"),
        initial_discipline=_require_number(initial_raw, "initial_discipline", path="$.initial_state"),
        initial_alignment=_require_number(initial_raw, "initial_alignment", path="$.initial_state"),
    )

    room_unlock_raw = _require_mapping(unlock_raw, "rooms", path="$.unlock_schedule")
    sup_unlock_raw = _require_mapping(unlock_raw, "supervisors", path="$.unlock_schedule")
    unlock_rooms = MappingProxyType({int(k): int(v) for k, v in room_unlock_raw.items()})
    unlock_sups = MappingProxyType({str(k): int(v) for k, v in sup_unlock_raw.items()})

    hidden_accumulators = HiddenAccumulatorConfig(
        rigidity_limen_security=_require_number(hidden_raw, "rigidity_limen_security", path="$.hidden_accumulators"),
        rigidity_discipline=_require_number(hidden_raw, "rigidity_discipline", path="$.hidden_accumulators"),
        radical_from_low_alignment=_require_number(
            hidden_raw, "radical_from_low_alignment", path="$.hidden_accumulators"
        ),
        radical_from_casualties=_require_number(hidden_raw, "radical_from_casualties", path="$.hidden_accumulators"),
        innovation_from_output=_require_number(hidden_raw, "innovation_from_output", path="$.hidden_accumulators"),
        innovation_from_upgrades=_require_number(hidden_raw, "innovation_from_upgrades", path="$.hidden_accumulators"),
    )

    guardrails = GuardrailConfig(
        early_days_max_casualties=_require_int(guardrails_raw, "early_days_max_casualties", path="$.guardrails"),
        early_days_casualty_cap_until_day=_require_int(
            guardrails_raw, "early_days_casualty_cap_until_day", path="$.guardrails"
        ),
        prevent_critical_before_day=_require_int(guardrails_raw, "prevent_critical_before_day", path="$.guardrails"),
    )

    return SimSimConfig(
        metadata=_freeze_mapping(metadata),
        worker_equations=worker_equations,
        absenteeism=absenteeism,
        accident=accident,
        productivity=productivity,
        base_rate_wu_by_room=_parse_float_room_map(base_rate_wu_by_room_raw, path="$.base_rate_wu_by_room"),
        room_capacities=_parse_room_capacities(room_caps_raw),
        economy=economy,
        lookup_tables=lookup_tables,
        security=security,
        conflicts=conflicts,
        confidence=confidence,
        critical_events=_freeze_mapping(critical_raw),
        outcome_tables=_parse_outcome_tables(outcome_raw),
        initial_state=initial_state,
        unlock_schedule_rooms=unlock_rooms,
        unlock_schedule_supervisors=unlock_sups,
        hidden_accumulators=hidden_accumulators,
        guardrails=guardrails,
    )
