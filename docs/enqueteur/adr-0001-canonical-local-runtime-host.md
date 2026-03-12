# ADR-0001: Canonical Local Runtime Host

- Status: Accepted
- Date: 2026-03-12

## Context

Enqueteur needed repo-local, turnkey live playability before post-H work.  
Before S1-S7, local runtime ownership was unclear across launch, live session transport, and frontend integration.

The project needed one canonical local path that contributors could run daily without adapter tribal knowledge.

## Decision

Adopt the canonical local runtime host as:

- single-process Python ASGI backend (`backend/server`)
- transport/lifecycle orchestration only
- framework-agnostic gameplay/runtime core remains separate (`backend/api`, `backend/sim4`)
- in-memory run registry as host source of launched-run attachment state
- explicit per-WebSocket session controller owning handshake, baseline, live command flow, diff emission, and teardown
- frontend as a separate Vite dev server (`frontend/enqueteur-webview`)
- optional frontend proxy convenience allowed, but backend remains runtime source of truth
- live path is canonical for human play; offline/replay remains secondary (debug/QA support)

## Consequences

Positive:

- contributors get a stable local launch/connect/play path
- transport concerns are centralized in server host modules
- gameplay logic stays reusable and framework-agnostic
- host hardening can evolve without moving truth ownership

Tradeoffs:

- run/session state is process-local and in-memory only
- stale run handling is local-dev oriented (lazy TTL cleanup), not a production lifecycle manager
- offline/replay remains available but is explicitly not the primary human play path

## What This Means for Future Work

- Keep route modules thin; keep protocol/session lifecycle in the session controller.
- Do not move gameplay semantics into `backend/server`.
- Treat the local live path as the default acceptance path for human playtests.
- If future work changes this architecture, write a new ADR rather than silently drifting.

## Read First

1. `README.md` (local quick start)
2. `docs/enqueteur/local_playtest_workflow.md` (playtest standard + troubleshooting)
3. `docs/enqueteur/local_runtime_host_spec_v1.md` (detailed host spec)
