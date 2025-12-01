Episode Identity Foundations (Sprint 1)
======================================

This document captures the foundational helpers and schema extensions added in Sprint 1 to support robust episode identity without changing any runtime behavior.

Goals of Sprint 1
- Add helper functions to work with identity purely from append-only JSONL logs.
- Extend the EpisodeRecord data structure with optional metadata.
- Add tests to lock in the helpers’ behavior and schema backward-compatibility.
- Do not change any CLI/API/simulation behavior (no functional changes).

Helpers (loopforge/analytics/identity_helpers.py)
- detect_latest_episode_identity(path: Path) -> Optional[tuple[str, str, int]]
  - Reads the action log JSONL (fail-soft).
  - Scans from the end and returns the most recent (run_id, episode_id, episode_index) found.
  - Skips malformed lines and rows missing identity fields; missing file -> None.
- verify_episode_identity_in_log(path: Path, run_id: str, episode_id: str, episode_index: int) -> bool
  - Streams the JSONL (fail-soft).
  - Returns True on the first matching row; missing file or no match -> False.

Schema Extension (loopforge/analytics/run_registry.py)
- EpisodeRecord gains two optional fields (default None):
  - status: str | None  (e.g., "resolved", "orphaned"; not used yet)
  - source: str | None  (e.g., "simulation", "cli-view-episode"; not used yet)
- Backward compatible: load_registry() treats missing fields as None; append writes them only if present.

Invariants (No Behavior Changes in Sprint 1)
- Logs remain append-only and fail-soft.
- Registry remains append-only and fail-soft.
- Analysis strictness is unchanged.
- CLI/API/simulation logic unchanged; helpers are not yet wired into control flow.

Future (Sprint 2 Preview)
- Integrate helpers to validate identities before registry append.
- Consider marking or skipping unresolved episodes at API boundaries with clear errors.
