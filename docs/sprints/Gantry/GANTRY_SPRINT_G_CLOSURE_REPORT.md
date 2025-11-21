Sprint G — LLM Shim Removal

Status: ✅ Complete
Agent: Junie
Architect: You
Date: 2025-11-20 20:23

1. Executive Summary

This sprint removed the two remaining root-level LLM shim modules and migrated all internal, test, and CLI imports to the canonical `loopforge.llm.*` namespace. No logic changed; behavior remains identical. The full test suite and CLI sanity checks passed. Narrative, Analytics, and the CLI shim were intentionally left untouched.

2. Objective & Scope

Objective
- Eliminate LLM-layer shims at the project root and normalize imports to canonical modules under `loopforge/llm/`.

In Scope
- Import path rewrites (internal code + tests)
- Deletion of root-level LLM shim files
- Zero logic changes

Explicitly Out of Scope
- Narrative modules (except import rewrites where applicable)
- Analytics modules/shims
- CLI shim (`scripts/run_simulation.py`)
- Any refactors within `loopforge/llm/*` beyond import normalization

3. Files Removed (root-level LLM shims)
- loopforge/llm_stub.py
- loopforge/llm_client.py

Presence audit result: Both shim files were present at the start of Sprint G and have been removed. All repository imports now point to canonical modules under `loopforge.llm.*`.

4. Canonical Import Rewrites

Internal
- loopforge/core/simulation.py — switched to `from loopforge.llm import llm_stub` and called via the module object (e.g., `llm_stub.decide_robot_action_plan_and_dict(...)`) to preserve test monkeypatch behavior.
- loopforge/cli/sim_cli.py — ensured analytics imports use canonical paths (e.g., `from loopforge.analytics import run_registry`), aligning with prior Analytics sprint and test monkeypatching.

Tests (representative list)
- tests/test_llm_stub.py — `import loopforge.llm.llm_stub as stub`
- tests/test_llm_client.py — `import loopforge.llm.llm_client as lc`
- tests/test_llm_stub_policy_pipeline.py — `from loopforge.llm import llm_stub`
- tests/test_narrative.py — `from loopforge.llm.llm_stub import decide_robot_action_plan`
- tests/test_simulation.py — `import loopforge.llm.llm_stub as stub`
- tests/test_memories.py — `import loopforge.llm.llm_stub as stub`
- Also normalized remaining analytics references where encountered (metrics/analysis_api/weave) to `loopforge.analytics.*`.

5. Verification

5.1 Test Suite
- Command: `pytest -q`
- Result: PASS (all tests green)

5.2 CLI Sanity
- `python -m scripts.run_simulation --steps 3 --no-db` → PASS (no import errors; expected in-memory output)
- `python -m loopforge.cli.sim_cli --steps 3 --no-db` → PASS (no import errors; matches previous output)

5.3 Behavior & Logging
- No schema or behavior changes.
- JSONL action logging and the Canonical Seam are unchanged; logging remains fail-soft.
- LLM seam remains monkeypatch-friendly via module-qualified calls.

6. Non-Goals Confirmed Untouched
- Narrative modules: unchanged (aside from import rewrites where they referenced analytics earlier).
- Analytics modules: unchanged in this sprint (imports already canonical).
- CLI shim (`scripts/run_simulation.py`): unchanged.

7. Risks & Mitigations
- Risk: Hidden import references to root-level LLM shims.
  - Mitigation: Repo-wide targeted import audit; comprehensive test coverage across LLM-dependent modules; CLI smoke tests.

8. Outcome & Next Steps
- Outcome: LLM layer fully canonicalized to `loopforge.llm.*`; root-level LLM shims removed.
- Next: Proceed with repo-wide import normalization (Sprint I) and documentation updates (Sprint J) per roadmap when scheduled.

9. Commit
- Message: `chore(refactor): remove llm shim modules and migrate imports to canonical paths`
- Includes: Deletions of root-level LLM shims and import rewrites as enumerated above.

– Junie
