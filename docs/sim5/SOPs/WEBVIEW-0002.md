# Loopforge React Webview — AAA Path Guidelines (for Frontend LLM Architect)
**Audience:** Frontend Architect implementing the React webview viewer for Loopforge (Sim4 now, SimX later).  
**Goal:** Ship a “viewer-proof” AAA webview that is **protocol-first**, **deterministic**, **engine-agnostic**, and **future-portable**, aligned with **KVP-0001**.

---

## 0) Non-Negotiables (Constitution)
These rules are higher priority than performance hacks, framework trends, or convenience.

1. **Viewer is a pure client**
    - Viewer never imports kernel code.
    - Viewer never runs simulation logic.
    - Viewer only *observes* + *emits input commands*.

2. **Protocol is the system**
    - If it’s not expressed in KVP, it is not part of Loopforge.
    - All state derives from KVP messages and deterministic artifacts.

3. **Determinism is sacred**
    - Replay defines truth.
    - Same seed + inputs = same outputs.
    - Viewer must never affect determinism.

4. **Primitives-only payload contract**
    - Viewer treats payloads as boring data.
    - No engine-specific assumptions.
    - No implicit contracts beyond schema.

5. **Time belongs to kernel**
    - Viewer does not invent ticks.
    - Viewer does not “advance” history beyond delivered tick order.

---

## 1) React Architecture Positioning (RSC/SSR Reality Check)
We can use modern React/Next.js patterns for *web-app chrome* (navigation, run library UI, auth), but **the viewer core remains a client-only island**.

### Allowed to be Server-rendered (safe)
- Run list / metadata pages
- Auth / permissions gating
- Pre-flight artifact discovery (URLs, manifests)
- Static UI shell around viewer (layout, headers)

### Must be Client-only (sacred)
- KVP transport (WebSocket / HTTP replay fetching)
- State reconstruction (snapshots + diffs)
- Tick store, scrubbing, playback, caching
- Render loop (Canvas/WebGL/DOM)
- Desync detection + recovery logic

> Rule of thumb: if it depends on tick state, it’s client-owned.

---

## 2) Core Component Split (Recommended)
**Server components**: “shell + data retrieval that doesn’t depend on ticks.”  
**Client components**: “viewer engine + live state.”

Suggested structure:
- `app/run/[runId]/page.tsx` (server): fetch run metadata + artifact pointers; render shell
- `ViewerRoot.tsx` (client): owns KVP session + replay logic + rendering
- `ViewerHUD.tsx` (client): timeline, scrubbing, overlays, perf stats
- `RunSidebar.tsx` (server/client boundary): metadata can be server; live status is client

Hard rule: no server component may attempt to render tick-dependent UI.

---

## 3) KVP-First Viewer Runtime Model
The viewer runtime is a deterministic state machine driven by KVP messages and/or replay artifacts.

### Mandatory phases
1. **Handshake**
    - Send `VIEWER_HELLO`
    - Receive `KERNEL_HELLO`
    - Validate `kvp_version.major` and `schema_version`
    - Cache `render_spec` (must be stable across run)

2. **Subscribe**
    - Send `SUBSCRIBE` with channels and policies
    - Wait for `SUBSCRIBED`
    - Do not assume unsolicited data will arrive

3. **Baseline**
    - Acquire baseline `FULL_SNAPSHOT` (live: `snapshot_policy: ON_JOIN`; replay: nearest keyframe)
    - Build canonical in-memory state

4. **Streaming**
    - Apply `FRAME_DIFF` in strict order
    - Verify tick continuity (`from_tick` must equal current tick)
    - Verify `step_hash` policy (see desync section)

5. **Interaction**
    - Viewer emits `INPUT_COMMAND` only (no state mutation)
    - Commands are targeted to tick (`tick_target`)
    - Await `COMMAND_ACCEPTED/REJECTED`

---

## 4) Deterministic State Store Rules
Your store is an implementation detail, but its behavior must be deterministic.

### Store invariants
- State is a function of: `(baseline snapshot, ordered diff stream)`
- Arrays/lists must be treated with canonical ordering rules (as defined in payload canonicalize)
- Quantized floats must remain quantized (do not “pretty” them)

### Recommended internal model
- `currentTick: number`
- `entitiesById: Map`
- `roomsById: Map`
- `itemsById: Map`
- `eventsByTick: Map` or “replace list” strategy aligned with diff body
- `narrativeOverlayByEntity: Map` (tag nondeterministic)

### Anti-patterns
- Deriving “new truth” from rendering outputs
- Using wall-clock time to drive simulation state
- Mutating state outside the “apply snapshot/diff” pipeline
  md
  Copy code
## 5) Replay / Seek / Scrub (AAA Expectations)
The webview must feel instant, stable, and correct. Seek must not require replay from tick 0.

### Required replay capabilities (aligned with KVP + sprint direction)
- Jump to any tick via:
    1) load nearest keyframe (`FULL_SNAPSHOT`)
    2) apply diffs forward to target tick
- Support “scrub” UX without stutter:
    - prefetch ahead
    - keep a keyframe cache window
    - avoid blocking the main thread

### Recommended caching strategy
- Cache keyframes (snapshots) at intervals
- Cache diff chunks by tick range
- Evict using LRU by memory cap

### Strict correctness checks
- Applying diffs:
    - must be contiguous (no dropped ticks)
    - must match `from_tick → to_tick`
- If continuity breaks:
    - treat as invalid stream
    - request recovery: `SNAPSHOT_ON_DESYNC` policy or re-seek

---

## 6) Desync Detection & Recovery (Viewer Responsibilities)
Viewer verifies determinism via `step_hash` and can report mismatch.

### Minimum policy
- On each applied diff, store `lastStepHash`
- If computed/expected hash mismatch:
    - emit `DESYNC_REPORT`
    - wait for kernel response:
        - `DESYNC_CONFIRMED` + new `FULL_SNAPSHOT`
        - or `DESYNC_DENIED`
- On confirmed desync:
    - hard reset viewer state from provided snapshot
    - do NOT attempt “partial fixes”

### Hashing rule
Viewer must never invent step_hash semantics.
- If viewer does not compute its own hash, it can still verify:
    - step continuity
    - payload validity
    - optional “replay integrity file” if present (future)

---

## 7) Render Spec Handling (KERNEL_HELLO.render_spec)
`render_spec` is REQUIRED in v0.1 and is the viewer’s only engine-agnostic guidance for rendering.

### Rules
- Treat `render_spec` as immutable per run.
- Use it for:
    - coordinate system
    - projection hints
    - draw order hints
    - local sort key policy
    - asset fallback behavior
- Never infer additional meaning (no hidden rules).

### Camera + bounds
- Use `bounds` for initial camera fit and minimap scaling.
- Maintain deterministic camera defaults; user camera moves are local-only UI state.

---

## 8) Narrative & Psycho Overlays (Non-Authoritative)
Narrative data is viewer-facing and must not affect kernel logic.

### Handling rules
- `nondeterministic` fragments:
    - must be tagged and visually distinguishable if needed
    - can be replaced/expire via TTL
- Must never influence:
    - entity state
    - movement
    - events
    - any deterministic state

Overlay pipeline should be separate from the canonical world state pipeline.
Think “UI layer,” not “truth layer.”

---

## 9) Input Commands (Viewer → Kernel)
Viewer sends commands, never state.

### Required behavior
- Commands are validated client-side for shape only (schema)
- Kernel is authority; viewer must handle rejection gracefully
- Every command has:
    - `client_cmd_id` (uuid)
    - `tick_target`
- Viewer should maintain a “pending commands” UI state for feedback.

### Hard prohibitions
- Direct movement commands
- Direct state mutation
- Imperative scripting

Only indirect influence:
- WORLD_NUDGE
- DEBUG_PROBE
- REPLAY_CONTROL
- View control hints (non-deterministic, ignorable)

---

## 10) Performance: AAA Constraints Without Breaking Determinism
Performance must not introduce nondeterminism.

### Required
- Off-main-thread diff parsing when possible (Web Worker)
- Incremental rendering (do not block UI during prefetch)
- Avoid runaway re-renders (React performance hygiene)

### Forbidden
- Dropping ticks to “keep up”
- Applying diffs out of order
- “Best effort” state merges that violate canonical rules

### Recommended
- Separate “state apply” from “render”:
    - state apply builds canonical state
    - render consumes read-only snapshots of canonical state
- Use a frame scheduler:
    - render at display rate
    - apply diffs at tick rate, but never reorder

---

## 11) Error Handling & UX Contracts
Errors terminate sessions explicitly in KVP; treat them as first-class states.

Viewer must display:
- schema mismatch (hard stop)
- kvp major mismatch (hard stop)
- stream invalid (offer re-seek / reload)
- transport disconnect (offer resubscribe)

UI states should be explicit:
- `DISCONNECTED`
- `HANDSHAKING`
- `SUBSCRIBING`
- `LOADING_BASELINE`
- `PLAYING`
- `PAUSED`
- `SEEKING`
- `DESYNC_RECOVERY`
- `ERROR_FATAL`

---

## 12) Testing Requirements (Golden Traces)
This viewer must be testable by construction.

Minimum test suite:
- Golden snapshot decode + canonicalize
- Golden diff decode + canonicalize
- Apply snapshot + N diffs → expected deterministic state
- Seek test: keyframe + diffs → expected tick state
- Desync handling test: mismatch triggers report + recovery snapshot resets

No tests = not AAA.

---

## 13) “Do Not Accidentally Break This” Checklist
Before merging:
- [ ] Viewer can run with **zero kernel code imports**
- [ ] Viewer state derives only from snapshot+diff streams
- [ ] SSR does not render tick-dependent UI
- [ ] No wall-clock time in canonical state
- [ ] Diff application is contiguous + ordered
- [ ] `render_spec` is treated as immutable
- [ ] Narrative overlay cannot affect canonical state
- [ ] Desync recovery resets from full snapshot
- [ ] Golden tests cover apply + seek
  md
  Copy code
## 14) Implementation Notes (Opinionated Defaults)
These are recommended defaults that keep us on the AAA path.

### Next.js / React defaults
- Use Next.js App Router if desired, but keep viewer in a `use client` boundary.
- Keep viewer bundle lean:
    - avoid heavyweight state libs unless necessary
    - consider a dedicated store (Zustand or custom) with strict invariants

### Data formats & transport
- Live mode: WebSocket frames (KVP envelope)
- Replay mode: HTTP fetch of deterministic artifacts (index/keyframes/diffs)
- Codec boundary is sacred:
    - decoding/parsing must be swappable (JSON now, msgpack later)
    - never leak codec assumptions into the viewer’s core logic

### Rendering layer
- React is UI orchestration; rendering should be:
    - Canvas/WebGL for world
    - DOM for HUD/controls
- Rendering never writes back into canonical state.

---

## 15) Questions the Frontend Architect Must Answer (in design doc)
1. How does the viewer represent “baseline + diffs” internally while guaranteeing canonical ordering?
2. What’s the seek pipeline (keyframe selection + diff fetch window + apply)?
3. How are diff parsing and application offloaded (worker vs main thread)?
4. What are memory caps and eviction policies for caches?
5. How is `render_spec` enforced and prevented from drifting?
6. What’s the desync policy, and how does the UI represent recovery?
7. How do we ensure SSR is only “shell” and cannot hydrate tick-dependent markup?

If any answer implies “server computes viewer state,” it violates KVP.
md
Copy code
## Appendix: One-Sentence North Star
**The webview is a deterministic, protocol-driven playback client that can be swapped like an engine—React is just the skin, KVP is the spine.**