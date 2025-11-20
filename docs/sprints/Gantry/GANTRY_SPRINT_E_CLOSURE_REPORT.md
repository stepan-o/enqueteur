Sprint E — Narrative Shim Removal

Status: ✅ Complete
Agent: Junie
Architect: You
Date: 2025-11-20 13:00

1. Executive Summary

This sprint removed all remaining root-level Narrative shim modules and migrated all internal, test, and CLI imports to the canonical `loopforge.narrative.*` namespace. No logic changed; behavior remains identical. Full test suite and CLI sanity checks passed. Analytics, LLM, and CLI shims were intentionally left untouched.

2. Objective & Scope

Objective
- Eliminate Narrative-layer shims living at the project root and normalize imports to canonical modules under `loopforge/narrative/`.

In Scope
- Import path rewrites (internal code + tests + CLI references where applicable)
- Deletion of root-level Narrative shim files
- Zero logic changes

Explicitly Out of Scope
- Analytics shims
- LLM shims (`loopforge.llm_stub`, `loopforge.llm_client`)
- CLI shim (`scripts/run_simulation.py`)
- Any refactors within `loopforge/narrative/*` beyond import normalization

3. Files Removed (root-level Narrative shims)
- loopforge/daily_logs.py
- loopforge/episode_recaps.py
- loopforge/psych_board.py
- loopforge/story_arc.py
- loopforge/narrative_reflection.py
- loopforge/narrative_fusion.py
- loopforge/characters.py
- loopforge/narrative_viewer.py
- loopforge/memory_line.py
- loopforge/pressure_notes.py
- loopforge/explainer_context.py
- loopforge/explainer.py
- loopforge/llm_lens.py

4. Canonical Import Rewrites

Internal
- loopforge/cli/sim_cli.py — imports updated to `loopforge.narrative.*` for: `episode_recaps`, `characters`, `daily_logs`, `psych_board`, `narrative_viewer`, `explainer_context`, `explainer`, `llm_lens`.
- loopforge/narrative/episode_recaps.py — internal references normalized to `loopforge.narrative.memory_line` and `loopforge.narrative.pressure_notes`.

Tests (representative list)
- tests/test_narrative_viewer.py — `loopforge.narrative.narrative_viewer`
- tests/test_narrative_attribution.py — `loopforge.narrative.narrative_viewer`
- tests/test_narrative_emotion_overlay.py — `loopforge.narrative.narrative_viewer`
- tests/test_narrative_viewer_trends.py — `loopforge.narrative.narrative_viewer`
- tests/test_episode_recaps.py — `loopforge.narrative.episode_recaps`
- tests/test_episode_recaps_attribution.py — `loopforge.narrative.episode_recaps`
- tests/test_episode_story_arc_integration.py — `loopforge.narrative.episode_recaps`, `loopforge.narrative.story_arc`
- tests/test_story_arc_derivation.py — `loopforge.narrative.story_arc`
- tests/test_daily_logs.py — `loopforge.narrative.daily_logs`
- tests/test_daily_logs_attribution.py — `loopforge.narrative.daily_logs`
- tests/test_daily_logs_emotion_overlay.py — `loopforge.narrative.daily_logs`
- tests/test_psych_board.py — `loopforge.narrative.psych_board`
- tests/test_psych_snapshot.py — `loopforge.narrative.daily_logs`
- tests/test_memory_line.py — `loopforge.narrative.memory_line`, `loopforge.narrative.episode_recaps`
- tests/test_micro_incidents.py — `loopforge.narrative.episode_recaps`
- tests/test_world_pulse.py — `loopforge.narrative.episode_recaps`
- tests/test_supervisor_weather.py — `loopforge.narrative.episode_recaps`
- tests/test_narrative_reflection.py — `loopforge.narrative.narrative_reflection`
- tests/test_narrative_fusion.py — `loopforge.narrative.narrative_fusion`
- tests/test_llm_lens.py — `loopforge.narrative.llm_lens`
- tests/test_explainer.py — `loopforge.narrative.explainer`, `loopforge.narrative.explainer_context`

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
- Analytics shims and modules: unchanged.
- LLM shims (`loopforge.llm_stub`, `loopforge.llm_client`): unchanged.
- CLI shim (`scripts/run_simulation.py`): unchanged.

7. Risks & Mitigations
- Risk: Hidden import references to root-level shims.
  - Mitigation: Repo-wide targeted import audit; full test coverage across narrative modules; CLI smoke tests.

8. Outcome & Next Steps
- Outcome: Narrative seam fully canonicalized to `loopforge.narrative.*`; root-level Narrative shims removed.
- Next: Keep docs aligned (optional follow-up: update any docs referencing `loopforge/narrative.py` or `loopforge/types.py` to `loopforge/narrative/narrative.py` and `loopforge/schema/types.py`).

9. Commit
- Message: `chore(refactor): remove narrative shim modules and migrate imports to canonical paths`
- Includes: Deletions of root-level Narrative shims and import rewrites as enumerated above.

– Junie
