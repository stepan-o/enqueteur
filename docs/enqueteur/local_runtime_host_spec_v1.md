---

# Enquêteur Local Runtime Host Spec v1.0

## Purpose

Provide a **repo-local, turnkey live runtime host** for Enquêteur so the game can be launched and manually played from this repo without hidden external adapter wiring.

This host must make the following path real and documented:

* start backend locally
* start frontend locally
* launch MBAM from menu
* connect via live WebSocket
* receive `FULL_SNAPSHOT`
* play through the case
* reach recovery or accusation resolution
* repeat this reliably during development

This host is the bridge between:

* the existing deterministic Python gameplay/runtime core
* the existing Enquêteur live protocol
* the frontend viewer shell

It is **not** a redesign of gameplay architecture, protocol, or truth ownership.

---

# 1. Goals

## Primary goals

1. Add a **canonical in-repo backend entrypoint** for local live play.
2. Expose the required local endpoints:

    * `POST /api/cases/start`
    * `WS /live`
3. Keep the current Python gameplay/runtime core **framework-agnostic**.
4. Centralize WebSocket session lifecycle ownership in one clear place.
5. Support deterministic seeded runs for reliable playtesting.
6. Support the frontend’s normal path:

    * loading
    * main menu
    * case select
    * connecting
    * live game
7. Make local development simple and documented.

## Secondary goals

1. Support future demo/showcase packaging without architectural rewrite.
2. Improve clarity of live-path ownership vs legacy/offline tooling.
3. Provide a stable foundation for later polish work.

---

# 2. Non-goals

This spec does **not** do the following:

1. It does not redesign KVP-0001 or KVP-ENQ-0001.
2. It does not move gameplay logic into FastAPI/Starlette endpoint code.
3. It does not introduce persistence/DB-backed runs.
4. It does not make offline/replay the primary mode.
5. It does not deepen gameplay semantics by itself.
6. It does not implement showcase mode, audio, or post-H presentation polish.
7. It does not generalize Enquêteur into a multi-case platform beyond what is already needed for MBAM.

---

# 3. Architectural principles

## 3.1 Boundary rule

The backend host must be split into two layers:

### A. Core gameplay/runtime layer

Owns:

* deterministic case generation
* truth ownership
* simulation/runtime state
* command application
* projection generation
* protocol-compliant message building helpers already in backend

This layer must remain **framework-agnostic**.

### B. Transport/adapter layer

Owns:

* HTTP endpoint binding
* WebSocket accept/send/receive
* connection lifecycle
* session controller
* run lookup
* subscribe tracking
* diff pump task management
* disconnect cleanup
* local dev configuration

This layer may use FastAPI/Starlette/Uvicorn.

## 3.2 No framework leakage

The transport layer may call into the core, but:

* FastAPI request models must not become gameplay models
* WebSocket object types must not leak into case/runtime modules
* no endpoint should contain substantive gameplay logic

## 3.3 Live-first rule

The canonical player path is:

* HTTP launch
* WebSocket session
* live snapshot/diff stream

Offline/replay remains secondary.

## 3.4 Single local backend service

For current scope, one Python backend service owns:

* case launch
* run registry
* live WebSocket session
* diff streaming

No service split.

## 3.5 Deterministic-first playtesting

The local host must make seeded MBAM runs stable and easy to repeat.

---

# 4. Chosen technology shape

## Canonical host shape

A **single-process Python ASGI backend** using:

* **FastAPI** or thin Starlette-compatible structure
* **Uvicorn** as local server runner
* separate frontend Vite dev server
* optional Vite proxy to backend for convenience

FastAPI is acceptable as the transport shell because it gives:

* easy HTTP route wiring
* native WebSocket support
* clean startup/shutdown hooks
* ergonomic local development

But the host must remain thin.

---

# 5. Proposed module layout

This is a recommended shape, not a mandatory exact naming contract, but the separation of responsibilities must hold.

```text
backend/
  server/
    app.py                # ASGI app construction
    config.py             # local runtime config
    routes_http.py        # POST /api/cases/start binding
    routes_ws.py          # WS /live binding
    session_controller.py # per-connection WS lifecycle
    run_registry.py       # in-memory run storage + lookup
    models.py             # transport-only request/response schemas
    errors.py             # transport-facing error mapping
    lifespan.py           # app startup/shutdown wiring
```

The existing modules remain the source of truth for gameplay/runtime behavior, especially:

* `backend/api/cases_start.py`
* `backend/api/live_ws.py`
* `backend/api/live_commands.py`
* `backend/sim4/host/sim_runner.py`
* MBAM case modules

The new server layer should orchestrate them, not replace them.

---

# 6. Canonical responsibilities

## 6.1 `app.py`

Owns:

* ASGI app creation
* route registration
* lifespan attachment
* CORS if needed for local frontend
* health endpoint if included

Must not contain gameplay logic.

## 6.2 `routes_http.py`

Owns:

* binding `POST /api/cases/start`
* decoding request body
* transport validation
* calling existing launch/start logic
* returning launch metadata

Must not:

* build gameplay state itself
* duplicate case validation rules already present in the core

## 6.3 `routes_ws.py`

Owns:

* binding `WS /live`
* accepting connection
* delegating all session handling to `SessionController`

Must stay thin.

## 6.4 `session_controller.py`

This is the most important new ownership point.

Owns, per connection:

* WebSocket accept
* parsing inbound messages
* initial handshake sequencing
* run attachment
* subscription validation
* baseline snapshot send
* command receive loop
* diff pump task lifecycle
* disconnect handling
* cancellation/cleanup
* transport-level logging

This is the canonical owner of session flow.

## 6.5 `run_registry.py`

Owns:

* active runs in memory
* launch-time registration
* run lookup by id/session token
* reference counting or last-activity timestamps if needed
* stale-run cleanup policy if included

Must not:

* become a gameplay state manager
* mutate run semantics beyond registry concerns

---

# 7. Runtime model

## 7.1 Run

A run is a deterministic game instance created by `POST /api/cases/start`.

A run must contain or reference:

* run id
* case id
* seed
* difficulty/profile metadata
* runtime/kernel/runner instance
* protocol identity metadata
* launch/session token data as needed by the frontend contract
* creation timestamp
* optional last activity timestamp

## 7.2 Session

A session is a WebSocket attachment to a launched run.

A session is not the same as a run.

One run may later support:

* one active viewer only, or
* more than one viewer

For current scope, local play can assume **single active player viewer per run** unless the current protocol already supports more. The spec should not depend on multi-viewer support.

## 7.3 Registry policy

Use **in-memory registry only** for now.

Implications:

* server restart invalidates active runs
* no persistent resume
* acceptable for dev/playtest scope

---

# 8. HTTP contract

## 8.1 Endpoint

`POST /api/cases/start`

## 8.2 Purpose

Create a new deterministic run and return metadata needed for the frontend to open the live session.

## 8.3 Request

The transport layer may use request schemas, but they must map cleanly onto the existing launch semantics.

Fields should support the existing frontend launch needs, including:

* case id
* seed
* difficulty
* profile/mode

The backend remains responsible for validating:

* known case
* allowed difficulty/mode
* valid seed handling

## 8.4 Response

Return the launch metadata the frontend expects, including at minimum:

* run id
* websocket URL
* protocol identity:

    * engine name
    * schema version
* seed and relevant launch configuration
* any session token or connection metadata required by current app flow

The response shape must stay aligned with the existing frontend launch client and tests.

## 8.5 Failure handling

Return clear errors for:

* unknown case
* malformed launch request
* unsupported mode/profile
* invalid seed configuration
* internal launch failure

Transport errors must not leak Python internals in user-facing payloads.

---

# 9. WebSocket contract

## 9.1 Endpoint

`WS /live`

## 9.2 Purpose

Host the Enquêteur live session defined by KVP-0001 + KVP-ENQ-0001.

## 9.3 Session authority

The backend is authoritative.
The frontend is a viewer/input client.

## 9.4 Required sequencing

The session controller must enforce the protocol sequence expected by current docs/tests:

1. WS connection accepted
2. receive `VIEWER_HELLO`
3. validate launch/session identity
4. send `KERNEL_HELLO`
5. receive `SUBSCRIBE`
6. validate requested channels / session state
7. send `SUBSCRIBED`
8. send `FULL_SNAPSHOT`
9. enter live command + diff loop
10. send `FRAME_DIFF` messages as state changes occur

The exact message content remains governed by the existing live protocol implementation.

---

# 10. Session controller state machine

The per-connection controller must have an explicit internal lifecycle.

## States

### 10.1 `CONNECTED`

Socket accepted, no protocol messages validated yet.

### 10.2 `HELLO_VERIFIED`

`VIEWER_HELLO` accepted and matched to the launched run/session metadata.

### 10.3 `SUBSCRIBED`

`SUBSCRIBE` accepted and channels resolved.

### 10.4 `BASELINE_SENT`

`FULL_SNAPSHOT` sent successfully.

### 10.5 `LIVE`

Normal interactive state. Commands may be received and diffs may be emitted.

### 10.6 `CLOSING`

Disconnect, protocol violation, or server-side shutdown cleanup in progress.

### 10.7 `CLOSED`

Terminal state.

## State transition rules

The controller must reject or close on illegal message ordering, for example:

* command before baseline
* subscribe before hello
* malformed envelope
* protocol identity mismatch

The behavior should follow current protocol tests and error handling expectations.

---

# 11. Diff pump ownership

This is the key implementation requirement.

## 11.1 Rule

The session controller must explicitly own the background task or loop that emits diffs after baseline.

## 11.2 Responsibilities of the diff pump

It must:

* observe runtime updates for the attached run
* produce protocol-compliant diffs
* send them only after successful subscription/baseline
* stop cleanly on disconnect or session termination
* not leak orphaned tasks

## 11.3 Command interaction

Commands may cause immediate or queued state changes. The controller must ensure that:

* command acknowledgements/rejections are sent as required
* resulting diffs are streamed coherently
* no duplicate or out-of-order pump lifecycle occurs because of host confusion

## 11.4 Cleanup

On disconnect:

* cancel diff task
* detach from run/session cleanly
* release controller-owned resources
* optionally mark run inactive or leave it idle for TTL-based cleanup

---

# 12. Run registry spec

## 12.1 Purpose

Keep active launched runs available for WS attachment.

## 12.2 Core operations

Must support:

* create/register run
* get run by id or token
* mark session attached
* mark session detached
* remove run
* optional sweep stale runs

## 12.3 TTL policy

Recommended initial policy:

* keep detached runs briefly for dev friendliness
* optional TTL such as 10–30 minutes
* sweep on interval or lazily on write/read

This is convenience, not persistence.

## 12.4 Concurrency assumptions

The registry must be safe for:

* multiple requests
* multiple websocket connections
* async access in the chosen ASGI runtime

A simple in-memory async-safe design is enough.

---

# 13. Startup and shutdown behavior

## 13.1 Startup

The backend app startup should:

* initialize registry
* initialize any app-scoped config
* expose routes
* log local runtime readiness

## 13.2 Shutdown

The backend app shutdown should:

* cancel active session tasks
* close active runs cleanly if needed
* avoid leaving dangling async tasks
* log a clean shutdown summary

---

# 14. Local dev flow

## 14.1 Canonical dev topology

Two-process development flow:

### Backend

* Python ASGI server via Uvicorn

### Frontend

* Vite dev server

Frontend talks to backend over local HTTP/WS.

## 14.2 Proxy

Vite proxy is allowed for convenience, but the backend remains the canonical runtime host.

The system must still be conceptually valid even without the proxy.

## 14.3 Canonical local URLs

Define one documented default pair, for example:

* backend: `http://localhost:8000`
* frontend: `http://localhost:5173`

If a proxy is used, document how the frontend resolves:

* launch endpoint
* WebSocket endpoint

## 14.4 Required documented commands

The repo must document the exact steps to run:

* backend
* frontend
* tests
* manual playtest flow

---

# 15. Modes and profiles

The local runtime host must support the current intended profiles without ambiguity.

At minimum, it must cleanly pass through:

* `dev`
* `playtest`
* `demo`

The host itself must not embed gameplay-mode policy beyond transport concerns.

However, the host and docs should define:

## 15.1 Blessed daily local playtest path

Default should be:

* MBAM
* Seed A
* D0
* playtest profile

## 15.2 Demo path

Still separate from daily dev path. The host must not hardcode demo behavior into normal local play.

---

# 16. Legacy/offline boundary policy

The repo currently contains both:

* legacy/offline/replay surfaces
* Enquêteur live surfaces

The new host must clarify, not worsen, this split.

## Policy

1. Live runtime host is canonical for human play.
2. Offline/replay remains available for QA/debug.
3. New host code must use Enquêteur live naming/contracts.
4. Do not route new local human play through legacy schema/channel assumptions.
5. Any compatibility shims must be isolated and explicitly secondary.

---

# 17. Error handling

## 17.1 Categories

The adapter must distinguish:

* transport errors
* protocol errors
* launch validation errors
* missing run/session errors
* internal server errors

## 17.2 HTTP errors

Should return clean structured errors with safe messaging.

## 17.3 WS errors

The controller should:

* reject invalid protocol states/messages cleanly
* send appropriate error or close behavior consistent with current contract/tests
* log details server-side
* avoid crashing app-level process from one bad client

## 17.4 Missing/expired run behavior

If frontend tries to connect to a run that no longer exists:

* fail clearly
* preserve a readable UX path for reconnect failure on frontend

---

# 18. Observability and logging

This phase does not require full telemetry, but local runtime clarity matters.

## 18.1 Required logs

Log at least:

* app startup
* app shutdown
* run creation
* run id + seed + case id
* websocket connection opened
* hello verified
* subscribed
* baseline sent
* disconnect
* protocol rejection
* run cleanup

## 18.2 Log style

Use concise structured-ish logs suitable for local debugging.

Do not spam low-level protocol dumps by default.

## 18.3 Debug toggles

Optional verbose protocol logging may exist behind config flags.

---

# 19. Config

## 19.1 Config purpose

Support local host tuning without putting policy into code.

## 19.2 Suggested config items

* host
* port
* allowed frontend origins
* run TTL
* log level
* optional verbose protocol logging
* optional dev cleanup settings

## 19.3 Config rule

Config affects transport/runtime host behavior only, not canonical case truth.

---

# 20. Security and scope assumptions

This is a local/dev-oriented runtime host. Security needs are limited but basic hygiene still applies.

## 20.1 Current assumptions

* local trusted development environment
* no auth system required for this phase
* no public multi-tenant deployment assumptions

## 20.2 Still required

* no unsafe raw exception traces in normal API responses
* basic origin handling for local frontend
* avoid accidental wide-open production-like assumptions in docs

---

# 21. Testing requirements

The host is only successful if it becomes truly playable and testable.

## 21.1 New backend integration tests

Add tests for the real ASGI app entrypoint covering:

* `POST /api/cases/start` success
* invalid start payload failure
* websocket hello flow
* subscribe flow
* full snapshot delivery
* command loop on real app wiring
* disconnect cleanup
* missing run behavior

## 21.2 Frontend integration expectations

Existing frontend tests should continue to pass with the new host contract.

Additional tests may validate:

* frontend can target documented local backend URLs/config
* launch/connect error states remain coherent

## 21.3 Manual acceptance test

A human must be able to:

1. start backend
2. start frontend
3. launch MBAM from menu
4. connect successfully
5. inspect/interact
6. complete a run
7. restart and repeat

This is a required acceptance gate, not optional.

---

# 22. Acceptance criteria

The spec is complete only when all of the following are true.

## 22.1 Repo-local live playability

The repo alone provides a documented way to run the backend and frontend and reach `LIVE_GAME`.

## 22.2 Full startup flow works

The normal player-facing flow works:

* loading
* main menu
* case select
* connecting
* live game

## 22.3 Protocol compliance preserved

The live host respects KVP-0001 and KVP-ENQ-0001 sequencing and identity requirements.

## 22.4 Full snapshot and diff streaming work

After subscription, baseline arrives and subsequent interaction updates propagate correctly.

## 22.5 One full MBAM run is manually playable

At minimum on:

* Seed A
* D0
* playtest profile

## 22.6 No framework leakage into core

Gameplay/runtime modules remain framework-agnostic.

## 22.7 Clean session cleanup

Disconnects do not leave orphaned stream tasks or corrupted run state.

## 22.8 Tests remain green

Backend and frontend suites pass, with new host tests added.

## 22.9 Docs are updated

Repo docs clearly explain:

* how to run backend
* how to run frontend
* how to manually playtest
* what the canonical local flow is

---

# 23. Recommended implementation sequence

This is not yet the Codex phase plan, but it is the implementation order implied by the spec.

## Step 1

Create the ASGI app shell and config/lifespan scaffolding.

## Step 2

Bind `POST /api/cases/start` to the existing launch logic.

## Step 3

Add in-memory run registry.

## Step 4

Implement `WS /live` through a dedicated session controller.

## Step 5

Wire baseline send and diff pump lifecycle explicitly.

## Step 6

Add cleanup, TTL, and disconnect handling.

## Step 7

Add backend entrypoint tests.

## Step 8

Update frontend dev configuration/proxy if needed.

## Step 9

Update README/dev docs with exact run/play steps.

## Step 10

Run human manual acceptance playtest and fix gaps.

---

# 24. Explicit design decisions

## Decision 1

**Use a single Python ASGI backend service.**
Reason: simplest correct local topology.

## Decision 2

**Keep the core gameplay/runtime framework-agnostic.**
Reason: preserves architecture and prevents web-framework contamination.

## Decision 3

**Use in-memory run registry only.**
Reason: correct for current local/dev scope.

## Decision 4

**Make session controller the explicit owner of WS lifecycle and diff streaming.**
Reason: removes the current adapter ambiguity.

## Decision 5

**Keep live play canonical and offline/replay secondary.**
Reason: aligns repo reality with intended product direction.

## Decision 6

**Do not make Vite/Node the canonical runtime host.**
Reason: frontend convenience must not redefine backend truth.

---

# 25. Exit condition for this spec

This spec is considered fulfilled when Enquêteur is no longer “implemented in tests but missing the local host,” and instead becomes:

* repo-local
* live-launchable
* manually playable
* repeatable for daily development
* ready for the next phase family

That is the gate needed before the post-H presentation roadmap should begin in earnest.

---

If you want, next I’ll turn this into a **Codex-ready implementation prompt** for the first phase: building the ASGI host, run registry, and WS session controller.
