Sprint F — Analytics Shim Removal

Status: ✅ Complete
Agent: Junie
Architect: You
Date: 2025-11-20 17:03

1. Executive Summary

This sprint removed all remaining root-level Analytics shim modules and migrated all internal, test, and CLI imports to the canonical `loopforge.analytics.*` namespace. No logic changed; behavior remains identical. The full test suite and CLI sanity checks passed. Narrative, LLM, and CLI shim files were intentionally left untouched.

2. Objective & Scope

Objective
- Eliminate Analytics-layer shims living at the project root and normalize imports to canonical modules under `loopforge/analytics/`.

In Scope
- Import path rewrites (internal code + tests + CLI references where applicable)
- Deletion of root-level Analytics shim files
- Zero logic changes

Explicitly Out of Scope
- Narrative modules (aside from import rewrites)
- LLM shims (`loopforge.llm_stub`, `loopforge.llm_client`)
- CLI shim (`scripts/run_simulation.py`)
- Any refactors within `loopforge/analytics/*` beyond import normalization

3. Files Removed (root-level Analytics shims)
- loopforge/reporting.py
- loopforge/analysis_api.py
- loopforge/metrics.py
- loopforge/supervisor_activity.py
- loopforge/weave.py
- loopforge/run_registry.py

Presence audit result: These six shim files were present at the start of Sprint F and have been removed. All repository imports now point to canonical modules under `loopforge.analytics.*`.

4. Canonical Import Rewrites

Internal
- loopforge/cli/sim_cli.py — imports updated to `loopforge.analytics.*` for: `reporting`, `analysis_api`, `supervisor_activity`, `run_registry`.

Tests (representative list)
- tests/test_reporting.py — `loopforge.analytics.reporting`
- tests/test_analysis_api.py — `loopforge.analytics.analysis_api`
- tests/test_analysis_with_ids.py — `loopforge.analytics.analysis_api`
- tests/test_analysis_by_id.py — `loopforge.analytics.analysis_api`
- tests/test_episode_export_shape.py — `loopforge.analytics.analysis_api`, `loopforge.analytics.reporting`
- tests/test_run_replay.py — `loopforge.analytics.analysis_api`, `loopforge.analytics.run_registry`
- tests/test_cli_view_episode_latest.py — `loopforge.analytics.run_registry` (via shim path normalization in tests)
- tests/test_run_registry.py — `loopforge.analytics.run_registry`
- tests/test_supervisor_activity.py — `loopforge.analytics.supervisor_activity`
- tests/test_compute_day_summary.py — `loopforge.analytics.reporting`
- tests/test_belief_attributions.py — `loopforge.analytics.reporting`
- tests/test_beliefs.py — `loopforge.analytics.reporting`

Developer Scratch
- scratch.py — `loopforge.analytics.analysis_api`

5. Verification

5.1 Test Suite
- Command: `pytest -q`
- Result: PASS (all tests green)

5.2 CLI Sanity
- `python -m scripts.run_simulation --steps 3 --no-db` → PASS (no import errors; expected in-memory output)
- `python -m loopforge.cli.sim_cli --steps 3 --no-db` → PASS (no import errors; matches previous output)

5.3 Behavior & Logging
- No schema or behavior changes.
- JSONL action logging path and shape unchanged; logging remains fail-soft.

6. Non-Goals Confirmed Untouched
- Narrative modules: unchanged (other than import rewrites where they referenced analytics).
- LLM shims (`loopforge.llm_stub`, `loopforge.llm_client`): unchanged.
- CLI shim (`scripts/run_simulation.py`): unchanged.

7. Risks & Mitigations
- Risk: Hidden import references to root-level analytics shims.
  - Mitigation: Repo-wide targeted import audit; comprehensive test coverage across analytics-dependent modules; CLI smoke tests.

8. Outcome & Next Steps
- Outcome: Analytics layer fully canonicalized to `loopforge.analytics.*`; root-level Analytics shims removed.
- Next: Proceed to Sprint G (LLM Shim Removal) per roadmap once approved.

9. Commit
- Message: `chore(refactor): remove analytics shim modules and migrate imports to canonical paths`
- Includes: Deletions of root-level Analytics shims and import rewrites as enumerated above.

– Junie
