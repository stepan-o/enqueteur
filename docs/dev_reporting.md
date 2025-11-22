Developer Investigation & Incident Report Template
================================================

This template is required for all bug investigations, failing test analysis, and behavioral regressions. Include this (filled) template in your PR description or link to a checked‑in report under docs/reports/ when the write‑up is lengthy.

Keep narrative clarity high and speculation low. Trim stack traces to the most informative portions.

---

1) Executive Summary
- What failed (single sentence)
- Scope of impact (who/what is affected)
- Root cause in brief (1–2 bullets)
- Chosen fix and why (1–2 bullets)
- Verification outcome (pass/fail summary)

2) Environment Matrix
Provide exact versions you used to reproduce and verify. Fill all that apply.

- OS: macOS/Linux/Windows + version
- Python: x.y.z (uv/venv/conda), pip/uv version
- Node: x.y.z (for UI work), npm/pnpm/yarn version
- SQLAlchemy: x.y.z
- Database URL used during tests: e.g. sqlite+pysqlite:///loopforge_test.db or postgresql+psycopg://…
- Extra services: Docker (version), Postgres (version)

3) Reproduction Steps
Exact commands and environment variables. Example:

    export DATABASE_URL=sqlite+pysqlite:///loopforge_test.db
    uv sync
    pytest -q

Include any seed data or files if required.

4) Failure Surface
- Failing tests/modules/files (list)
- Error types and top stack frames (trimmed)
- Whether the failure occurs at import/collection or during execution
- Any nondeterminism observed (flaky behavior)

5) Root Cause Analysis
- Primary cause: what specific condition produced the failure?
- Contributing factors: configuration coupling, import‑time side effects, etc.
- Why now? (regression window if known)
- How you validated the cause (experiments, toggles, logs)

6) Proposed Fix Options
Always list the minimal, stability‑first option first. For each option:
- Description
- Pros/cons
- Risk level
- Backward‑compatibility notes (API, schema, logs, The Seam)
- Expected blast radius

Then state your chosen option and justification.

7) Verification Plan
- Automated tests to run (unit, integration, UI)
- Manual checks and expected outputs
- Data migration implications (if any)
- Rollout plan (behind flag? docs changes?)

8) Risks, Mitigations, and Rollback
- Known risks
- Mitigations you implemented
- Simple rollback plan (how to revert the change safely)

9) Follow‑ups (Non‑blocking)
- Tech debt or refactors to consider later
- Monitoring/observability items
- Documentation gaps discovered

---

Example (Current Backend Test Failures)
--------------------------------------

This is an example filled for the current failing backend tests to illustrate the expected depth.

1) Executive Summary
- Failure: 9 backend test modules error during collection.
- Impact: Entire backend test suite cannot run locally or in CI without extra deps/config.
- Root cause: (1) psycopg missing while SessionLocal binds a Postgres engine at import time; (2) fastapi not installed for API tests.
- Chosen fix (proposed): Configure tests to use SQLite via DATABASE_URL and document required test deps; optionally add lazy engine creation as a later refactor.
- Verification: With DATABASE_URL=sqlite+pysqlite:///loopforge_test.db and FastAPI installed, tests collect; further failures TBD by actual run.

2) Environment Matrix
- OS: macOS 14 (example)
- Python: 3.11.x via uv
- SQLAlchemy: project‑pinned
- DB URL: default Postgres (failing) vs. sqlite+pysqlite:///loopforge_test.db (passing collection)

3) Reproduction Steps

    # Failing path
    pytest -q
    # ImportError: psycopg, ModuleNotFoundError: fastapi

    # Passing collection path (proposed)
    export DATABASE_URL=sqlite+pysqlite:///loopforge_test.db
    pip install fastapi httpx  # or add to optional test extras
    pytest -q

4) Failure Surface
- Failing files:
  - tests/test_cli_view_day_latest.py
  - tests/test_cli_view_episode_latest.py
  - tests/test_events.py
  - tests/test_explainer.py
  - tests/test_memories.py
  - tests/test_phase4_logging_and_traits.py
  - tests/test_run_replay.py
  - tests/api/test_episodes_api.py
  - tests/api/test_health.py
- Error types: ModuleNotFoundError: psycopg, ModuleNotFoundError: fastapi
- Phase: Import/collection, due to loopforge.db.db binding an engine at import time and API tests importing FastAPI TestClient

5) Root Cause Analysis
- Primary: Eager engine creation SessionLocal = sessionmaker(bind=get_engine()) pulls Postgres driver immediately.
- Secondary: API tests rely on FastAPI not listed as a default dependency in the base environment.
- Validation: Setting DATABASE_URL to SQLite avoids psycopg import‑time error; installing FastAPI resolves TestClient import error.

6) Proposed Fix Options
1) Environment‑only fix (minimal):
   - Install fastapi and httpx; set DATABASE_URL=sqlite+pysqlite:///loopforge_test.db for tests.
   - Pros: No code changes; respects stability.
   - Cons: Requires discipline in CI/local setup.
   - Risk: Low.
2) Code refactor (needs approval):
   - Lazy engine creation or bind sessionmaker later.
   - Pros: Import‑safe without DB driver; better modularity.
   - Cons: Touches DB layer; risk of subtle behavior changes.
   - Risk: Medium.

Chosen: (1) for now; document clearly in CONTRIBUTING.

7) Verification Plan
- Run full pytest -q after configuring env and deps.
- Ensure API tests pass with FastAPI installed.
- Confirm no backend behavioral changes (only environment).

8) Risks, Mitigations, and Rollback
- Risks: None to runtime; only documentation/config expectations.
- Mitigations: Clear docs and Makefile targets if needed.
- Rollback: Revert documentation changes.

9) Follow‑ups
- Consider extras_require[test] with FastAPI/httpx and a pytest.ini that sets SQLite DB URL during tests.

---

10) Implemented Fix & Current State — 2025-11-22 13:13

Implemented fix:
- Added tests/conftest.py that sets DATABASE_URL to sqlite+pysqlite:///loopforge_test.db for the pytest session. This removes the import‑time requirement for the Postgres driver (psycopg) and a running Postgres instance by ensuring SQLAlchemy binds an SQLite engine during tests.

Current state:
- Backend: pytest runs to completion with 100% passing tests in the current environment.
- Frontend: Vitest suite passes (smoke test), confirming test runner wiring.
- Stability: No changes to runtime behavior, API surfaces, schemas, or logging. The modification is strictly a test‑environment configuration and is fully backward‑compatible.
- Rollback: Delete tests/conftest.py or override DATABASE_URL in the environment to restore previous behavior.