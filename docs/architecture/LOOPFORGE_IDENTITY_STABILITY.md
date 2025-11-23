🌿 Loopforge Identity Stability — Implementation Sprint Plan
(Two sprints: Sprint 1 = foundations, Sprint 2 = behavioral changes)
🚀 Sprint 1 — Foundations (Safe, No Behavioral Changes)

Duration: ~5–7 days of focused dev time
Goal: Add all foundational helpers, schemas, and guardrails without changing API or CLI behavior.

✅ Outcomes

New helper functions exist, fully tested.

Registry gains optional status and source fields.

No changes to simulation, analysis, CLI, or API behavior.

Zero risk, zero regressions.

🔧 Sprint 1 Tasks
1. Add Helper: detect_latest_episode_identity()

Purpose: Extract latest (run_id, episode_id, episode_index) from action logs.
Location: loopforge/analytics/helpers_identity.py (new module).

Requirements:

Reads action log JSONL.

Scans in reverse order.

Coalesces last contiguous block with the same identity.

Returns a tuple or None.

Never throws.

Tests:

Empty log.

Log with multiple runs.

Log with mixed identities.

Missing fields → return None.

2. Add Helper: verify_episode_identity_in_log()

Purpose: Quick validation before registry append.
Location: same module as above.

Requirements:

Returns True if any log row matches identity.

Treat missing log file as False.

Must be fast (streaming).

Tests:

Exact match.

Wrong ID.

Missing fields.

Mixed episodes.

3. Extend EpisodeRecord Schema with Optional Fields

File: run_registry.py

Add fields (all optional, default None):

status: str | None
source: str | None


Constraints:

Must be backward compatible.

load_registry() must tolerate old rows.

append_episode_record() must write new fields if provided.

No behavior change yet.

Tests:

Round-trip serialization.

Backward compatibility.

4. No-Behavior-Change Integration

Temporarily add the helper imports to:

sim_cli.py

run_registry.py

analysis_api.py

…but DO NOT call them yet.

This ensures future diffs are smaller.

5. Documentation

Add:

docs/dev/episode_identity_foundations.md

Containing:

Purpose of helpers

Test coverage rules

How future sprints will integrate them

🧪 Sprint 1 Deliverables

New helper module

Tests for both helpers

Extended EpisodeRecord model

Fully passing test suite

No functional changes anywhere else

Documentation added

🚀 Sprint 2 — Behavioral Changes (Minimal, Safe, High-impact)

Duration: 7–10 days
Goal: Make the system self-consistent without breaking workflows.

🔥 Outcomes

view-episode no longer writes synthetic IDs that don’t exist.

Registry only holds “resolved” entries.

API responds gracefully with structured errors.

Identity invariants enforced end-to-end.

🔧 Sprint 2 Tasks
1. Integrate Identity Detection Into view-episode

Rules:

When no IDs are provided by user:

Try detect_latest_episode_identity().

If found → use it.

If NOT found → DO NOT append registry; warn user.

When IDs ARE provided:

verify_episode_identity_in_log() must return True before registry append.

If false → warn and skip registry write.

Tests:

Happy path.

No logs.

Conflicting logs.

Synthetic case → must not create record.

2. Registry Status Handling

When appending a record:

If identity verified → status = "resolved"

If identity fails → do NOT write (default policy)

But support writing orphaned records if architect changes policy later.

API will later pick up this field.

Tests:

Registry with mixed resolved/orphaned entries loads correctly.

Appending resolved rows sets fields properly.

3. API Behavior Enforcement

Endpoints to update:

GET /episodes

Include status and source fields if present.

Never break old clients.

GET /episodes/latest

Selection logic:

Choose latest record where status == "resolved".

If none:

Return 404 with JSON:

{
"detail": "No resolved episodes available",
"code": "no_resolved_episode"
}


Error handling:

Catch ValueError from analysis.

Translate to structured error:

{
"detail": "Episode identity not found in logs",
"code": "orphaned_registry_record",
"run_id": "...",
"episode_id": "..."
}

GET /episodes/{episode_id}

Same rules as /latest.

Tests:

No resolved episodes.

Happy path.

Orphaned episodes.

Mixed registry entries.

Analysis mismatch error translation.

4. CLI Error Messaging

Clear messaging for:

“Identity could not be detected; no registry entry written.”

“Requested identity does not exist in logs.”

“Synthetic episode skipped.”

No regressions for:

replay-episode

export-stage-episode

sim with DB vs no-DB

5. Documentation Updates

Update docs/API.md for new error codes.

Update CLI usage docs.

Add “How identity works” in dev docs.

🧪 Sprint 2 Deliverables

Fully deterministic identity pipeline.

Zero synthetic-orphan mismatches.

Predictable API.

Tests for every identity path.

Updated documentation.

🏁 Post-Sprint Hardening (Optional)

(Architect decides later)

Add make run-steady-latest helper

Add profiling for big logs

Explore multi-episode-per-run

Explore identity shards per-run instead of single action log

🧱 Acceptance Criteria (for both sprints)
All tests pass

(no regressions)

No synthetic IDs ever reach registry

Unless explicitly marked as orphaned (future option)

/episodes/latest returns predictable 200 or structured error

Never a bare 500 and never a misleading episode.

Action log is the canonical identity source

Always.

Spec compliance 100%