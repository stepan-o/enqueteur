# Supervisor Activity — Deterministic Daily Scalar (Sprint 4)

Status: Implemented (read-only, deterministic)

What it is
- A pure, telemetry-derived scalar per day in [0,1] representing how often the Supervisor acted that day.
- Used only in the reporting/analysis path (DaySummary → Attribution/Reflection). It does not affect simulation behavior.

Definition
- supervisor_activity = (number of supervisor entries for the day) / steps_per_day, clamped to [0,1].
- If steps_per_day <= 0 → 0.0.

Where it is computed
- `loopforge/supervisor_activity.py`:
  ```python
  def compute_supervisor_activity(supervisor_entries_for_day: List[ActionLogEntry], steps_per_day: int) -> float:
      ...  # returns a clamped fraction in [0,1]
  ```

Wiring (read-only)
- CLI: `scripts/run_simulation.py:view_episode(...)`
  - If `supervisor_log_path` is provided and readable, supervisor JSONL lines are loaded and grouped by `day_index` (fallback: `step // steps_per_day` if needed).
  - For each `day_index`, `compute_supervisor_activity(...)` is called to get a scalar.
  - That scalar is passed to `compute_day_summary(..., supervisor_activity=val)`.
- Day runner: `loopforge/day_runner.py:compute_day_summary(...)`
  - Signature extended with kw-only `supervisor_activity: float = 0.0` (backward-compatible default).
  - The value is forwarded to `reporting.summarize_day(..., supervisor_activity=...)`.
- Reporting: `loopforge/reporting.py:summarize_day(...)`
  - Already accepts `supervisor_activity`; feeds it into belief attribution and reflection derivations.

Where it is used
- Attribution: `loopforge/attribution.py::derive_belief_attribution(...)` uses supervisor_activity (>= 0.6 considered "active") in rule selection.
- Reflection: `loopforge/narrative_reflection.py::derive_reflection_state(...)` stores it as `AgentReflectionState.supervisor_presence` (clamped) for narrative consistency.

Determinism & constraints
- No randomness. No LLM calls.
- No changes to the simulation loop or JSONL write schemas. Only reads logs.
- Additive-only API updates with safe defaults.

Tests
- `tests/test_supervisor_activity.py` — unit tests for helper (empty day, half steps, clamp >1, zero steps).
- `tests/test_supervisor_activity_wiring.py` — verifies the threaded scalar appears in `reflection_states[name].supervisor_presence` when passed via `compute_day_summary`.

Notes
- CLI grouping expects supervisor JSON lines to carry `day_index`; if absent, it falls back to `step // steps_per_day` when available.
- If no supervisor log path is provided, activity remains 0.0 (current default behavior), keeping earlier outputs intact.
