# Episode Identity — Sprint 2 Report

Date: 2025-11-22 20:01 (local)

## Scope Recap
Sprint 2 focuses on CLI + registry identity discipline only. We enforce that view-episode derives identities from logs and never writes registry entries with synthetic or mismatched IDs. Analysis and Stage API behavior remain unchanged in this sprint. Simulation and logging internals are untouched.

## Changes Implemented
- loopforge/cli/sim_cli.py
  - view-episode now:
    - Uses detect_latest_episode_identity(action_log_path) when IDs are not provided.
    - Verifies identities with verify_episode_identity_in_log(...) before appending to the registry.
    - Skips append and emits a concise message when identity cannot be resolved from logs or when explicit IDs do not exist in logs.
    - When appending, sets status="resolved" and source="cli-view-episode" on EpisodeRecord (backward-compatible fields added in Sprint 1).
  - All other behavior (episode computation, recap/narrative printing, JSON shapes) unchanged.

- tests/test_cli_view_episode_identity.py (new)
  - Scenario A (happy path): Action log contains a coherent identity block; view-episode (no IDs) appends a registry entry with matching IDs and status="resolved", source="cli-view-episode".
  - Scenario B (no identity in logs): Empty/ID-less log → no registry append; stderr contains message "Could not determine episode identity from logs; no registry entry was written." Episode summary still prints.
  - Scenario C (explicit IDs not in logs): Mismatched explicit IDs → verification fails; no append; stderr includes "Registry entry not written: no matching log entries found ...".

## Invariants Now Enforced
- CLI no longer writes registry entries with synthetic identities that are not present in the action log.
- view-episode derives IDs from logs via detect_latest_episode_identity when none are provided.
- Explicit identities must be found in the action log (at least one matching row) before a registry append occurs.
- When a registry append occurs via CLI, the record is marked status="resolved" and source="cli-view-episode" (optional, backward-compatible fields).

## Tests
- Added: tests/test_cli_view_episode_identity.py
  - test_view_episode_latest_happy_path_appends_verified_registry
  - test_view_episode_no_identity_in_logs_skips_registry
  - test_view_episode_explicit_ids_not_in_logs_skips_registry
- Existing backend and frontend tests remain green.
- Commands run:
  - uv run pytest
  - (frontend) npm run test (ui-stage)
  - Final status: all tests passed.

## How to Use (Developer Cheatsheet)
```
make reset-local
uv run loopforge-sim --no-db --steps 60
uv run loopforge-sim view-episode --latest
# The registry entry now mirrors the real log identity if found.
# If identity cannot be determined from logs, no registry entry is written and a one-line message is printed.
```

## Open Questions / Future Sprints
- API hardening: /episodes/latest should skip unresolved/orphaned records and surface explicit error codes (404 vs 422) — planned for a later sprint.
- Non-CLI writers (if any) may also need to adopt verification helpers.
- Legacy LLM execution paths: confirm they always write ID-bearing logs or clearly disallow Stage summaries for those runs.
- Performance: detect_latest_episode_identity currently reverse-reads into memory; consider a chunked reverse reader for very large logs.
