# sim_sim_1 Config Schema

Source of truth: [`/Users/stpn/Documents/repos/my_projects/loopforge/backend/sim_sim/config/sim_sim_1.default.yaml`](/Users/stpn/Documents/repos/my_projects/loopforge/backend/sim_sim/config/sim_sim_1.default.yaml)

This document defines required fields for the `sim_sim_1` runtime config loaded by `backend/sim_sim/config/load.py`.

## Top-level object

Required keys:
- `metadata`
- `worker_equations`
- `formulas`
- `base_rate_wu_by_room`
- `room_capacities`
- `economy`
- `lookup_tables`
- `security`
- `conflicts`
- `confidence`
- `critical_events`
- `outcome_tables`
- `initial_state`
- `unlock_schedule`
- `hidden_accumulators`
- `guardrails`

## metadata
- `config_name`: string
- `schema_version`: string (`sim_sim_1`)
- `spec_ref`: string path

## worker_equations
All float coefficients from Spec v1 §5:
- `alpha_h`, `alpha_f`, `alpha_k`, `alpha_r`, `alpha_p`
- `beta_l`, `beta_p`, `beta_s`, `beta_f`
- `gamma_p`, `gamma_i`, `gamma_k`, `gamma_s`

## formulas
- `absenteeism`: `{base, stress_coeff, discipline_coeff}`
- `accident`: `{base, low_discipline_coeff, high_stress_coeff, low_equipment_coeff}`
- `productivity`: `{base, discipline_coeff, stress_coeff, refactor_base, refactor_discipline_coeff, refactor_stress_coeff}`

## base_rate_wu_by_room
Map room id string -> float base WU/day used in pipeline step 16:
- `Cap_r = base_rate_wu_by_room[r] * (hours_r/9) * equipment_r`

## room_capacities
Object keyed by room id as string (`"1".."6"`), value:
- `max_dumb`: int
- `max_smart`: int
- `max_total`: int
- `no_workers`: bool (optional)

## economy
- `brains_per_wu`: int
- `wash_capacity_per_wu`: int
- `substrate_gal_per_wu`: int
- `ribbon_yards_per_wu`: int
- `sell_washed_dumb`: int
- `sell_washed_smart`: int
- `convert_cost`: int
- `upgrade_recipe`: object (debug/reference; currently 1:1:1 recipe)

## lookup_tables
- `default_l`: float
- `default_i`: float
- `default_relief`: float
- `leadership_order`: supervisor code -> room id -> float
- `indoctrination_pressure`: supervisor code -> room id -> float
- `relief_baseline`: supervisor code -> (`default` and optional room ids) -> float
- `event_relief`: `{total_success, accident_free}`

## security
- `thrum_failure_chance`: float
- `c_or_t_absent_bonus_base`: float
- `c_or_t_absent_bonus_scale`: float
- `thrum_failure_extra_absent_flat`: float
- `random_keep_bias_cathexis`: float
- `random_keep_bias_thrum_success`: float
- `stiletto_pull_order`: int[]
- `witch_pull_order`: int[]
- `redistribution_bias`: object for debug labels

## conflicts
- `hostile_pairs`: `[ [supA, supB], ... ]`
- `discovered_discipline_delta`: float
- `discovered_loyalty_delta`: float
- `support_confidence_delta`: float
- `oppose_confidence_delta`: float
- `support_influence_delta`: float
- `oppose_influence_delta`: float
- `support_loyalty_delta`: float
- `oppose_loyalty_delta`: float
- `security_edge_priority`: int
- `edge_priority`: map `"2-3"|"2-4"|"4-5" -> int`
- `ideology_shift`: float

## confidence
- thresholds/timing:
- `threshold_tension`, `threshold_critical`, `cooldown_days_on_critical`
- drift/deltas:
- `base_drift_below_tension`, `tension_multiplier`
- `native_bonus`, `hated_penalty`, `unassigned_penalty`, `non_native_no_success_penalty`
- suppress penalties:
- `suppress_confidence_penalty`, `suppress_loyalty_penalty`, `suppress_influence_penalty`, `suppress_factory_stress_delta`
- `outcome_delta`: map outcome label -> float (`total_success`, `small_success`, `neutral`, `small_fiasco`, `total_fiasco`)
- `hated_rooms`: supervisor code -> room ids
- `tension_passives`: supervisor code -> passive deltas

## critical_events
Object keyed by supervisor code (`L`,`S`,`C`,`W`,`T`), each value is an object with event-specific magnitudes/durations/resets. Common fields:
- `name`: string
- `reset_confidence`: float
- `cooldown_days`: int

Additional fields are event-specific and consumed by kernel logic (shutdowns, multipliers, alignment inversion, political deltas, etc).

## outcome_tables
Object keyed by supervisor code, then room id, then weighted outcome rows:
- row fields include:
- `label`: string
- `weight`: number
- optional: `sup_mult`, `fiasco_severity`, `casualties_min`, `casualties_max`, `equipment_damage_min`, `equipment_damage_max`, and behavior flags (`repair_first`, `no_accidents`, `weaving_boost_next_day`, etc)

## initial_state
- `cash`: int
- `worker_dumb`: int
- `worker_smart`: int
- `inventory`: map resource -> int
- `initial_equipment_condition`: float
- `initial_stress_min`: float
- `initial_stress_max`: float
- `initial_discipline`: float
- `initial_alignment`: float

## unlock_schedule
- `rooms`: room id -> unlock day (`-1` means never)
- `supervisors`: supervisor code -> unlock day

## hidden_accumulators
- `rigidity_limen_security`: float
- `rigidity_discipline`: float
- `radical_from_low_alignment`: float
- `radical_from_casualties`: float
- `innovation_from_output`: float
- `innovation_from_upgrades`: float

## guardrails
- `early_days_max_casualties`: int
- `early_days_casualty_cap_until_day`: int
- `prevent_critical_before_day`: int

## Validation behavior

`parse_sim_sim_config` is strict for required keys and primitive types. Missing/invalid required fields raise `ConfigValidationError` with a path and this schema doc reference.
