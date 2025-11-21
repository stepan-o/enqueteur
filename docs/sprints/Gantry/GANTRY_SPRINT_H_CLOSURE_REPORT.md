Sprint H — CLI Shim Removal (scripts/run_simulation.py)

Status: ✅ Complete
Agent: Junie
Architect: You
Date: 2025-11-20 20:50

1. Executive Summary

This sprint removed the last remaining CLI shim `scripts/run_simulation.py` and migrated all usage to the canonical Typer application `loopforge.cli.sim_cli`. No logic changed; this was an imports-only + deletion sprint. The full test suite is green and the canonical CLI works as expected.

2. Objective & Scope

Objective
- Eliminate the CLI shim wrapper and rely exclusively on `loopforge.cli.sim_cli` as the entry point.

In Scope
- Import path rewrites in tests and developer tooling to reference the canonical CLI.
- Deletion of `scripts/run_simulation.py`.
- Zero logic changes.

Explicitly Out of Scope
- Narrative modules
- Analytics modules
- LLM modules

3. Files Updated / Removed

Updated (imports/comments/tooling to canonical CLI):
- tests/test_cli_view_episode_latest.py — `from loopforge.cli.sim_cli import app`
- tests/test_cli_view_day_latest.py — `from loopforge.cli.sim_cli import app`
- tests/test_explainer.py — `from loopforge.cli.sim_cli import app as cli_app`
- tests/test_run_replay.py — `from loopforge.cli.sim_cli import app`
- tests/test_run_episode_ids.py — `from loopforge.cli import sim_cli as cli` (for monkeypatching)
- tests/test_run_registry.py — `from loopforge.cli import sim_cli as cli`
- loopforge/cli/sim_cli.py — usage strings reference `python -m loopforge.cli.sim_cli`
- pyproject.toml — `[project.scripts]` includes `loopforge-sim = "loopforge.cli.sim_cli:app"`
- Makefile — `run` target uses `python -m loopforge.cli.sim_cli`
- scripts/CHEATSHEET.md — examples reference canonical CLI
- main.py — pointer updated to `python -m loopforge.cli.sim_cli`
- loopforge_city.egg-info/entry_points.txt — console script points to canonical CLI module

Removed (final CLI shim):
- scripts/run_simulation.py

Presence audit result: The shim file existed at the start of Sprint H and was removed. All repository references now point to `loopforge.cli.sim_cli`.

4. Verification

4.1 Test Suite
- Command: `pytest -q`
- Result: PASS (all tests green)

4.2 CLI Sanity
- `python -m loopforge.cli.sim_cli --steps 3 --no-db` → PASS (expected in-memory output)

4.3 Behavior & Logging
- No schema or behavior changes.
- JSONL action logging path and shape unchanged; logging remains fail-soft.

5. Non-Goals Confirmed Untouched
- Narrative, Analytics, and LLM modules: unchanged (beyond prior sprints).

6. Risks & Mitigations
- Risk: Hidden references to the removed shim.
  - Mitigation: Targeted repo-wide import audit; tests for CLI commands; manual CLI sanity run.

7. Outcome & Next Steps
- Outcome: Canonical CLI entry point finalized; repository is now shim-free for CLI.
- Next: Proceed with Sprint I (repo-wide import normalization) and Sprint J (documentation updates) per roadmap when scheduled.

8. Commit
- Message: `chore(refactor): remove cli shim and migrate all usage to loopforge.cli.sim_cli`
- Includes: Deletion of `scripts/run_simulation.py` and import/tooling rewrites listed above.

– Junie
