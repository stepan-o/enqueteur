# Episode Identity & Logs/Registry Investigation (Phase 1)

Last updated: 2025-11-22 15:03 (local)

## 1. Executive Summary
- Problem: The Stage API endpoint GET /episodes/latest intermittently fails with: ValueError: No action log entries found for run_id=… and episode_id=…
- Root cause (best current understanding): The CLI path view-episode can generate synthetic run_id/episode_id values when it cannot resolve identities from logs, then appends an EpisodeRecord to the run registry containing those synthetic IDs. The analysis layer (analyze_episode_from_record → analyze_episode) strictly filters action logs by (run_id, episode_id) and requires IDs on every log row; if logs from the preceding simulation run do not contain matching IDs, analysis raises, and /episodes/latest surfaces the error.
- Implication: The registry and logs can desynchronize. The API’s convenience endpoint /episodes/latest selects a registry record whose IDs have no corresponding rows in logs/loopforge_actions.jsonl, causing a 500 at the API boundary or an unhandled exception if not wrapped.

## 2. Identity Lifecycle (Current Behavior)
High‑level path (above/below the seam noted):
- Simulation run (below the seam) → Action logs (JSONL) → Episode summaries (compute_day_summary + summarize_episode) → Run registry append (JSONL) → Analysis (read logs strictly by identity) → Stage builder → API response.

Concrete modules and fields:
- Logging & IDs
  - loopforge.schema.types.ActionLogEntry (class ActionLogEntry): Holds step, agent, plan, outcome, plus optional episode_index/day_index (lines ~598–668 in file).
  - loopforge.core.logging_utils:
    - JsonlActionLogger.write_entry/write_dict: Write JSON lines to logs/loopforge_actions.jsonl.
    - log_action_step(logger, perception, plan, action, outcome, *, episode_index, day_index, run_id, episode_id):
      - Builds an ActionLogEntry and then additively merges identity via identity_dict(run_id, episode_id, episode_index) if provided. Fail‑soft: identity merge is wrapped in try/except (lines ~76–95); logging itself is also fail‑soft (lines ~96–101).
    - read_action_log_entries(path): Reads JSONL, fail‑soft if file missing; skips malformed rows.

- ID generation utilities
  - loopforge.core.ids: generate_run_id(), generate_episode_id() are used by callers when needed.

- Registry
  - loopforge.analytics.run_registry:
    - @dataclass EpisodeRecord(run_id, episode_id, episode_index, created_at, steps_per_day, days, scenario_name?)
    - append_episode_record(record): appends to logs/loopforge_run_registry.jsonl (fail‑soft on I/O).
    - load_registry(): returns List[EpisodeRecord], skipping malformed rows.
    - latest_episode_record(): returns last row or None.

- Analysis layer
  - loopforge.analytics.analysis_api:
    - analyze_episode(...): reads action logs and strictly requires identity on all rows; if run_id/episode_id not provided, raises ValueError (lines ~110–116). Filters strictly by (run_id, episode_id); if no rows match, raises ValueError (line ~120).
    - analyze_episode_from_record(record, *, action_log_path, supervisor_log_path?): Validates the record and forwards to analyze_episode with record’s fields (lines ~186–209). No fallback logic.
    - episode_summary_to_dict(...): serialization helper (not identity-relevant beyond echoing run_id/episode_id back).

- API layer
  - loopforge/api/routers/episodes.py:
    - GET /episodes: returns registry rows (episode_id, run_id, episode_index, days, created_at).
    - GET /episodes/{episode_id}: finds record by episode_id, calls _build_stage_episode_from_record → analyze_episode_from_record → build_stage_episode().
    - GET /episodes/latest: selects “latest” record using _pick_latest_episode (explicit max over (created_at, episode_index)), then same build path.

Key invariant: The analysis layer is strict about ID presence and matching. If logs lack IDs or contain different IDs than the registry record, analysis fails.

## 3. Detailed Walkthrough of the Reproduction Scenario
Reference commands:

1) make reset-local
   - scripts/reset_local_state.py likely wipes or reinitializes logs/ and local DB state. Result: logs/loopforge_actions.jsonl may be deleted/reset; logs/loopforge_run_registry.jsonl may also be cleared.

2) uv run loopforge-sim --no-db --steps 60
   - Entry: loopforge/cli/sim_cli.py → run_simulation (below the seam). During steps:
     - log_action_step writes ActionLogEntry rows to logs/loopforge_actions.jsonl via JsonlActionLogger.
     - Identity injection depends on whether run_id/episode_id are passed into log_action_step calls. With --no-db and default paths, the simulation may not be propagating run_id/episode_id into each action entry. If no run/episode identity is passed, ActionLogEntry rows are written without run_id/episode_id (per log_action_step additive behavior).
     - Outcome: Action log likely contains entries with step/agent data but missing run_id/episode_id.

3) uv run loopforge-sim view-episode --steps-per-day 20 --days 3
   - Path: sim_cli.py view-episode handler (see around lines ~450–500 in current file snapshot):
     - Computes DaySummary objects by re‑reading the action log (compute_day_summary with action_log_path and entries param optional; for view-episode, it passes preloaded per‑day slices or the entries list accordingly).
     - Identity resolution: If run_id or episode_id is None, it tries to import generate_run_id and generate_episode_id (lines ~467–474):
       - run_id = generate_run_id()
       - episode_index = 0
       - episode_id = generate_episode_id(run_id, episode_index)
       - On error: falls back to “run-unknown” and ep timestamp or “ep-unknown”.
     - summarize_episode(..., episode_id=episode_id, run_id=run_id, episode_index=episode_index) builds an EpisodeSummary embedding those IDs.
     - Registry append: constructs EpisodeRecord using (episode.run_id, episode.episode_id, episode.episode_index, created_at=utc_now_iso(), steps_per_day, days) and calls append_episode_record(record) (lines ~487–501). This is fail‑soft but usually succeeds, so a registry row appears even if action logs were ID‑less.

   - Critical observation: The EpisodeRecord written here reflects synthetic IDs (generated now), not necessarily the IDs that exist in the previously written action log entries (which may have none). view-episode does not rewrite the logs; it only appends a registry record.

4) uv run loopforge-sim api-server; Browser calls:
   - GET /health → OK.
   - GET /episodes → reads registry via load_registry and returns a list — this works because it does not read logs.
   - GET /episodes/latest → selects the “latest” EpisodeRecord via _pick_latest_episode and calls analyze_episode_from_record(record, action_log_path=logs/loopforge_actions.jsonl).
     - analyze_episode_from_record forwards to analyze_episode with record-provided run_id/episode_id.
     - analyze_episode loads all_rows using _read_action_jsonl_raw and enforces that every row has run_id and episode_id (lines ~112–116). If any row lacks identity, it proactively raises ValueError("Action log contains rows without identity fields..."). If all rows do have identity but none match (run_id, episode_id), it raises ValueError("No action log entries found for run_id=... and episode_id=...") (line ~120).
     - Given the earlier simulation likely wrote ID‑less logs, the first check may trigger (rows missing IDs). Alternatively, if some entries had IDs from a different run and the synthetic IDs don’t match, the strict filter returns zero rows and triggers the "No action log entries found" error.

Empirical result expected per scenario: /episodes works; /episodes/latest fails with ValueError: No action log entries found for run_id=... and episode_id=...

## 4. Failure Analysis
- Why /episodes works:
  - It only reads the registry JSONL (append‑only metadata). It does not validate against logs, so it faithfully returns the EpisodeRecord(s) written by view-episode.

- Why /episodes/latest fails:
  - The registry’s record IDs (synthetic) do not correspond to any rows in the action log. The analysis layer strictly requires identity on every row and then filters by (run_id, episode_id), resulting in zero matching rows and a ValueError.
  - Two contributing cases:
    1) Missing IDs in logs: The simulation run wrote entries without run_id/episode_id, violating the analysis precondition that “Action log contains rows without identity fields” is not allowed.
    2) Mismatched IDs: Even if some identity exists, the record’s (run_id, episode_id) may not match the identities actually present in the log because view-episode generated them after the fact.

Conclusion: The mismatch is both due to missing IDs in the logs (for --no-db run) and a synthetic record identity appended by view-episode that doesn’t match the existing log entries.

## 5. Design Constraints & Invariants
- Must not break:
  - CLI flows: view-episode, replay-episode, export-episode, export-stage-episode.
  - Tests and monkeypatch patterns that assume current function signatures.
  - JSONL log shapes: append‑only, backward‑compatible; logs must remain fail‑soft and deterministic.
- Current code assumptions:
  - Analysis assumes identity is present and consistent on all action rows (strict).
  - Registry is an append‑only metadata file and does not enforce consistency with logs.
  - Single shared action log file (logs/loopforge_actions.jsonl) may contain entries from multiple runs; strict filtering by (run_id, episode_id) is the selection mechanism.

## 6. Option Space (High‑Level Only, No Implementation)
1) API‑side fallback
   - Idea: If analyze_episode_from_record finds zero rows (or detects ID‑less rows), fallback to a best‑effort mode: analyze the latest contiguous block of steps or the full log as a single episode.
   - Pros: Users get something instead of a hard error; quick to implement.
   - Cons: Blurs identity semantics; can misrepresent episodes; risks masking underlying data hygiene issues; complicates tests.
   - Risk: Medium; Behavior changes at API layer must be carefully documented; keep behind a flag.

2) Registry discipline
   - Idea: Only append EpisodeRecord when we have known, consistent run_id/episode_id that are already present in the log rows; otherwise, avoid or mark the record as unresolved.
   - Pros: Keeps registry authoritative and consistent with logs; failure moved earlier (CLI), making API simpler.
   - Cons: Requires surfacing a failure in view-episode if identity is missing; could be disruptive to workflows expecting a registry entry regardless.
   - Risk: Low‑Medium; Requires clear user feedback and documentation.

3) Stronger identity propagation
   - Idea: Ensure the simulation run (even --no-db) always propagates run_id/episode_id into every action log entry. For example, generate IDs at sim start and pass them through to log_action_step for every entry.
   - Pros: Restores strict identity invariants; analysis remains simple; registry and logs remain in sync.
   - Cons: Requires touching simulation paths and ensuring all callers to log_action_step pass identity; potential coupling to ID generation timing.
   - Risk: Medium; Must be introduced without breaking existing flows; requires tests to lock behavior.

4) Registry‑log consistency check (hybrid)
   - Idea: When appending an EpisodeRecord, optionally validate that at least one matching (run_id, episode_id) row exists in the action log; if not, write a record with a status flag (e.g., unresolved=true) to signal downstream consumers.
   - Pros: Preserves append‑only registry while signaling consistency level; API can decide how to handle unresolved records.
   - Cons: Adds schema fields (backward‑compatible) and downstream branching; more complexity.
   - Risk: Medium.

## 7. Recommendations for Next Steps
Decisions needed from the architect before implementation:
1) Identity source of truth: Should the logs be the canonical identity carrier (recommended), with registry entries only mirroring existing identities?
2) Tolerance vs strictness at API: Should /episodes/latest provide a fallback (best‑effort) or remain strict and explicit about missing IDs?
3) When to generate IDs: Should simulation runs always generate and propagate run_id/episode_id (even in --no-db mode) starting at step 0?
4) Registry schema: Are we permitted to add an optional status/flags field (e.g., unresolved, orphaned) for records without matching logs?
5) Testing: Approve adding tests that: (a) enforce IDs on all action rows during sim run, (b) ensure registry entries are only appended when identities exist in logs, (c) assert /episodes/latest succeeds end‑to‑end without mocks.

Suggested tests to add later (post‑decision):
- Simulation path test: run one small sim; assert all logged rows contain run_id/episode_id/episode_index.
- Registry append test: after view-episode, assert that registry record IDs appear in the log at least once.
- API integration test: seed logs + registry coherently; GET /episodes/latest returns 200 and matches IDs.
- Negative test: unresolved registry record yields 404 or a clear diagnostic (depending on chosen strategy).

## Appendix: Key Code References
- loopforge/core/logging_utils.py
  - log_action_step(): merges identity additively if provided; otherwise logs without identity (fail‑soft).
- loopforge/analytics/analysis_api.py
  - analyze_episode(): requires identity on all rows; filters strictly by (run_id, episode_id); raises ValueError when no rows match.
  - analyze_episode_from_record(): thin adapter that forwards registry’s identity to analysis.
- loopforge/cli/sim_cli.py (view‑episode path)
  - If run_id/episode_id not resolved from logs, generate synthetic IDs (generate_run_id/generate_episode_id) and append an EpisodeRecord to the registry. Does not backfill IDs into existing logs.
- loopforge/analytics/run_registry.py
  - EpisodeRecord, append_episode_record, load_registry, latest_episode_record.


## Phase 1.5 Follow-Up Findings

Last updated: 2025-11-22 18:35 (local)

### 1. Validated Assumptions
- Confirmed: The simulation path run_simulation does pass identity into logs.
  - Evidence: loopforge/core/simulation.py calls log_action_step with run_id, episode_id, and episode_index in BOTH no-DB and DB-backed branches (see lines ~169–178 and ~240–249). These IDs are constructed at sim start via generate_run_id and generate_episode_id, with fail-soft fallbacks.
- Confirmed: log_action_step propagates identity into each JSONL row if provided by the caller.
  - Evidence: loopforge/core/logging_utils.py merges identity_dict(run_id, episode_id, episode_index) into the base ActionLogEntry dict when any identity fields are provided.
- Refuted (per current code): “--no-db runs produce ID-less action logs.”
  - Current implementation passes IDs in both branches; ID-less rows would only occur if a different caller logs without passing identity or if an older/alternate path bypasses log_action_step.
- Partially confirmed: There exist code paths that can produce a registry EpisodeRecord with IDs that do not come from the log file.
  - Evidence: sim_cli.py:view-episode generates synthetic IDs when run_id/episode_id are None in that context and appends an EpisodeRecord to the registry. It does not backfill or rewrite action logs with these synthetic IDs.
- Uncertain (edge): If USE_LLM_POLICY=True or a legacy/alternate execution path bypasses log_action_step, logs may not be written or may be written without IDs.
  - Note in config: The JSONL step logger is “not currently wired into the legacy LLM path.” This could indirectly produce empty or non-ID logs depending on execution mode. We have not validated this path during this sprint.
- Neutral: The --no-db flag does not directly suppress ID injection; it only toggles persistence mode. Identity generation and passing are the same in both branches of run_simulation.

### 2. Ground Truth Timeline
```
Sim start
  └─ generate_run_id() → _run_id
  └─ episode_index := 0 → generate_episode_id(_run_id, episode_index) → _episode_id
  └─ open JsonlActionLogger for logs/loopforge_actions.jsonl

First action step
  └─ log_action_step(..., run_id=_run_id, episode_id=_episode_id, episode_index=0)
      → logs row with identity fields present

Day boundary (repeats per step)
  └─ Subsequent log_action_step(...) calls continue including IDs

view-episode (post-run CLI)
  └─ compute_day_summary(...) reading the action log
  └─ IF run_id/episode_id not available in that CLI context
       → generate_run_id()/generate_episode_id() again (synthetic IDs)
  └─ summarize_episode(..., episode_id=synthetic_or_resolved, run_id=synthetic_or_resolved)
  └─ append_episode_record(record with these IDs) → logs/loopforge_run_registry.jsonl

API call
  └─ /episodes → reads registry only → OK
  └─ /episodes/latest → select latest EpisodeRecord (explicit ordering)
      → analyze_episode_from_record(record)
        → analyze_episode(..., run_id=record.run_id, episode_id=record.episode_id)
          → read all action rows; require IDs on every row
          → strictly filter by (run_id, episode_id)
            • If synthetic IDs differ from logged IDs → zero matches → raise ValueError
```

Markers:
- IDs first appear: At sim start (run_simulation), before the first log_action_step.
- Synthetic IDs appear: In view-episode when it cannot resolve IDs from context and generates new ones.
- Mismatch introduced: When registry is appended with synthetic IDs that do not exist in the action log.
- Strict analysis rejection point: analyze_episode detects no rows matching (run_id, episode_id) and raises ValueError("No action log entries found ...").

### 3. Deterministic Reproduction Confirmation
For the sequence:

- make reset-local
- loopforge-sim --no-db --steps 60
- loopforge-sim view-episode --steps-per-day 20 --days 3
- GET /episodes/latest

From static code reading (no runtime), we can confirm:
- The action log should contain entries that include run_id and episode_id fields, because run_simulation passes them into every log_action_step in the no-DB branch (refuting the earlier blanket assumption of ID-less logs in this mode).
- view-episode may generate fresh (synthetic) IDs for the EpisodeSummary and EpisodeRecord if it does not resolve IDs from the log context.
- /episodes/latest will select the EpisodeRecord containing these fresh IDs (due to explicit ordering by created_at, then episode_index).
- analyze_episode_from_record will then strictly filter the action log rows by the registry’s run_id/episode_id. Since the log rows contain different IDs (the ones from the simulation run), the filter returns zero rows and raises ValueError("No action log entries found for run_id=... and episode_id=...").

Uncertainty/Notes:
- Whether view-episode has a code path to recover the original run_id/episode_id from logs is not visible in our static scan; current observed code shows it generates IDs when None.
- If a developer ran a simulation via an alternate path (e.g., legacy LLM decision route) that bypassed log_action_step, action logs might be ID-less or missing entirely, which would trigger the earlier check in analyze_episode ("Action log contains rows without identity fields"). Our primary scenario focuses on the strict-zero-match error, which is consistent with current run_simulation.

### 4. Architectural Decision Points
1. Canonical identity source of truth: Should action logs be the authoritative carrier of run_id/episode_id, with all downstream systems (registry, analysis) aligning to them?
2. Registry discipline: Should EpisodeRecord writes be allowed only when (run_id, episode_id) are known to exist in the action log, or should we permit synthetic IDs with an explicit unresolved status?
3. API tolerance: Should analysis remain strict (current) or gain a controlled degradation mode (fallback analysis, explicit 409/422/424 statuses, or a developer mode flag)?
4. Identity propagation timing: Must every simulation run (db/no-db, LLM/non-LLM) generate and propagate IDs from step 0, and are we willing to forbid execution paths that don’t?
5. Registry schema evolution: Are optional fields (e.g., unresolved=true, source="synthetic"|"derived-from-log") acceptable to signal consistency without breaking consumers?
6. API behavior on unresolved entries: Should /episodes/latest detect unresolved records and return 404 with a clear diagnostic, skip them, or surface a structured error code?
7. CLI ergonomics: Should view-episode refuse to append a registry record if it cannot resolve log identity, or should it prompt/write a record with unresolved status?

### 5. Proposed Test Fixture (description)
Goal: Reproduce the mismatch deterministically with minimal artifacts and no external services.

Artifacts/files:
- logs/loopforge_actions.jsonl — seeded with a handful of rows that include a consistent run_id="run-A", episode_id="ep-A", episode_index=0 (small, 5–10 lines). These can be captured from a tiny sim run or hand-constructed per ActionLogEntry schema.
- logs/loopforge_run_registry.jsonl — seeded with a single EpisodeRecord whose IDs are synthetic and do NOT match the action log (e.g., run_id="run-SYN", episode_id="ep-SYN", episode_index=0), with a recent created_at to make it the latest.

Steps:
1) Ensure the seeded registry contains only the synthetic EpisodeRecord mentioned above.
2) Start the API server (or instantiate the FastAPI app in tests).
3) Call GET /episodes to verify the synthetic EpisodeRecord appears (sanity check).
4) Call GET /episodes/latest and assert a 500 (or surfaced ValueError) with a message indicating no matching action log entries for the specified (run_id, episode_id).

Variations:
- A second registry record that correctly matches the log IDs (run-A/ep-A) placed earlier than the synthetic one to ensure ordering matters.
- An alternative fixture where the actions JSONL intentionally omits identity fields on one or more lines to assert the earlier identity-presence validation path.

Outcome:
- This fixture isolates the core bug (registry/log identity mismatch) without requiring a full simulation and is suitable for future automated tests once the architectural decisions are made.
