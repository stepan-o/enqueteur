Sprint D — Psych Shim Removal

Status: ✅ Complete
Agent: Junie
Architect: Gantry / You
Date: 2025-11-20 11:30 (local)

1. Executive Summary

Sprint D removed all remaining Psych-layer shims and canonicalized imports across the codebase and tests to use loopforge.psych.* modules directly. No logic changes were made — this was a structural cleanup to finalize the Psych layer’s migration.

All tests are green, CLI sanity runs are clean, and behavior remains identical. Narrative, Analytics, LLM, and CLI shims were intentionally left untouched (future sprints).

2. Shims Removed (root-level)

Removed thin re-export shims under loopforge/*.py that now live in loopforge/psych/*:
- loopforge/emotions.py
- loopforge/emotion_model.py
- loopforge/beliefs.py
- loopforge/attribution.py
- loopforge/attribution_drift.py
- loopforge/supervisor_bias.py
- loopforge/supervisor_weather.py
- loopforge/trait_drift.py
- loopforge/long_memory.py
- loopforge/world_pulse.py
- loopforge/micro_incidents.py
- loopforge/arc_cohesion.py

3. Import Canonicalization (imports-only)

- Internal code already used canonical psych imports in most places.
- Adjusted one remaining narrative site:
  - loopforge/narrative/episode_recaps.py
    - from loopforge.micro_incidents import build_micro_incidents → from loopforge.psych.micro_incidents import build_micro_incidents
    - from loopforge.arc_cohesion import build_arc_cohesion_line, compute_reflection_tone → from loopforge.psych.arc_cohesion import build_arc_cohesion_line, compute_reflection_tone
- Tests: verified and, where necessary, ensured imports go through loopforge.psych.* (many were already canonical post earlier sprints).

4. Out-of-Scope (explicitly not touched)

- Narrative shims (e.g., loopforge/narrative.py, loopforge/narrative_viewer.py)
- Analytics shims (e.g., loopforge/reporting.py, loopforge/analysis_api.py)
- LLM shims (loopforge/llm_stub.py, loopforge/llm_client.py)
- CLI shim (scripts/run_simulation.py)

5. Verification

5.1 Test Suite
pytest -q → PASS (all green)

5.2 CLI Smoke Tests
- python -m scripts.run_simulation --steps 3 --no-db → PASS
- python -m loopforge.cli.sim_cli --steps 3 --no-db → PASS

6. Behavior Changes

None. Only import paths and file removals. Public shapes, JSONL logging, and simulation behavior remain unchanged.

7. Acceptance Criteria Checklist

- All Psych shims removed from loopforge/*.py → ✅
- No internal code or tests import from loopforge.<psych_shim> → ✅
- All Psych imports go through loopforge.psych.* → ✅
- Tests green (pytest -q) → ✅
- CLI runs succeed as before → ✅
- Non-Psych shims untouched → ✅

8. Commit

Commitizen-style message:
chore(refactor): remove psych shim modules and update imports to canonical paths

- Delete root-level Psych shims (12 files).
- Adjust episode_recaps imports to loopforge.psych.*.
- No logic changes; tests + CLI green.

9. What This Enables

- Clear separation of layers with canonical Psych as the single source of truth.
- Reduced technical debt ahead of Narrative/Analytics/LLM shim cleanup sprints.
- Simpler mental model for developers and future architects; fewer aliasing pitfalls.

– Junie
