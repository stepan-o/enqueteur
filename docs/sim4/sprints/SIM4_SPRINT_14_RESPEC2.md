# Sprint 14 — KVP Replay Export (Offline, Viewer-First)

---

## 0) Scope Lock (Non-Negotiable)

Sprint 14 implements **ARTIFACT / OFFLINE replay only**.

- **No live kernel process**
- **No server**
- **No transport**
- **No WebSocket**
- **No handshake runtime**
- **No SUBSCRIBE/SUBSCRIBED**
- **No REPLAY_* control messages**
- **No viewer UI / rendering implementation**

**Sprint 14 reuses only:**
- KVP envelope (`kvp_version`, `msg_type`, `msg_id`, `sent_at_ms`, `payload`)
- message types + payload schemas for **`FULL_SNAPSHOT`** and **`FRAME_DIFF`**
- canonicalization + quantization + hashing rules (`step_hash` rules as defined)

**Sprint 14 does NOT exercise KVP session lifecycle semantics.**  
There is **no session**. There is **no negotiation**. There is **no kernel authority loop**.  
This sprint is **pure export + framing** of already-computed outputs.

---

## 1) Primary Goal

Export a completed simulation run into a **viewer-consumable replay folder** such that a frontend viewer (WEBVIEW-0002) can:

- load the run **offline** (disk or static HTTP)
- seek to any tick
- apply **keyframe snapshots + per-tick diffs** deterministically
- render placeholders (2.5D / isometric)
- overlay narrative bubbles + psycho topology (as sidecar streams)
- do all this **without knowing anything about Sim4/Sim5 internals**

**Success is:**
> A frontend engineer points the viewer at an exported run folder and says:  
> **“This is all I need.”**

---

## 2) Inputs (Assumed Already Produced by Sprints 9–13)

Sprint 14 assumes integration outputs exist (or are being finalized) including:

- Tick frames / state source
- Render specs (Room/Agent render-relevant data)
- Event/bubble streams (presentation)
- Psycho topology frames (presentation)

Sprint 14 must not change simulation behavior; it only packages outputs.

---

## 3) Outputs (What Sprint 14 Produces)

A deterministic export folder containing:

### A) `manifest.kvp.json` (Authoritative Run Index + Contract)
- run identity + anchors (`engine_name`, `engine_version`, `schema_version`, `world_id`, `run_id`, `seed`, `tick_rate_hz`, `time_origin_ms`)
- **`render_spec`** (required contract surface)
- tick window: `available_start_tick`, `available_end_tick`
- keyframe policy: **either** `keyframe_interval` **or** explicit `keyframe_ticks`
- inventory/pointers for:
    - `FULL_SNAPSHOT` keyframes
    - `FRAME_DIFF` records
    - overlay streams (X_* sidecars)
- integrity metadata (hashes / hash chain references)

**Note:** This file conceptually corresponds to the **KERNEL_HELLO artifact**, but it is not sent and does not imply a session.

### B) State records (KVP envelopes stored as artifacts)
- `FULL_SNAPSHOT` records (keyframes)
- `FRAME_DIFF` records (tick-to-tick)
- each record is an **independently decodable KVP envelope**
- ordering and integrity are enforced via manifest + hash chain rules

### C) Presentation overlays (Out of protocol)
- narrative/UI bubbles stream (X_* records)
- psycho topology stream (X_* records)

**Hard rule:** overlays must NOT appear inside `FULL_SNAPSHOT` or `FRAME_DIFF` payloads.

---

## 4) Protocol/Compliance Rules (Sprint 14 Binding)

### Envelope rules
- every state record MUST use the KVP envelope
- viewer decodes envelope first, dispatches only on `msg_type`

### State semantics
- `FULL_SNAPSHOT` is a complete baseline for declared channels
- `FRAME_DIFF` is a transition:
    - `to_tick = from_tick + 1` (v0.1 tick mode)
    - `prev_step_hash` must chain correctly
- viewer must be able to rebuild deterministically from:
    - snapshot at keyframe tick
    - diffs applied in ascending tick order

### Canonicalization
- canonical ordering + `Q1E3` quantization MUST be applied before hashing/emitting
- arrays sorted by stable IDs per invariants
- `ops[]` order is canonical “as emitted” (kernel/exporter must be stable)

### Hashing
- `step_hash` is computed on canonical resulting state at tick boundary
- in offline mode, integrity verification is driven by manifest references (hashes/chains)

---

## 5) File/Chunking Model (Exporter Concerns Only)

- chunking and paths are **artifact organization**, not protocol
- regardless of chunking:
    - each record remains independently decodable
    - record semantics remain per-tick diffs and keyframe snapshots
- viewer discovers everything via `manifest.kvp.json` (no hidden conventions)

---

## 6) Deliverables

### Required code deliverables
- `integration/schema_version.py` (already planned) and schema SSoT
- Sprint 14 exporter module(s) that:
    - take a completed run output
    - canonicalize + quantize
    - emit manifest + records + indexes + sidecars
    - produce a folder that WEBVIEW-0002 can consume

### Required test deliverables
- golden export fixture folder (small run)
- verifier test:
    - loads manifest
    - replays snapshots + diffs
    - validates tick continuity + hash chain + schema invariants

---

## 7) Out of Scope (Explicit)

- LIVE transports, handshake, subscription, replay control messages
- server endpoints
- viewer UI
- rendering logic
- simulation logic changes

Anything that smells like runtime behavior is out.

---

## 8) Sub-sprint plan

## 9) Sprint 14 — Juno-Friendly Subsprints (Offline KVP Replay Export)

> Goal: Export a completed run into a **manifest + KVP-enveloped snapshots/diffs + sidecars**
> such that WEBVIEW-0002 can load offline, seek, scrub, rewind, and render deterministically.
>
> Non-negotiable: **no live kernel / no transport / no REPLAY_* / no handshake**.

---

### S14.0 — Guardrails + “Bulletproof” Scope Lock
**Goal:** make it impossible to accidentally build live/session behavior.

**Deliverables**
- `docs/sprint14_scope_lock.md` (short, loud, copy/paste into PRs)
- Exporter README header comment template (must appear atop exporter entrypoint)
- A “non-goals checklist” included in code review template

**Acceptance**
- Any mention of WebSocket/handshake/SUBSCRIBE/REPLAY_* is flagged in code review checklist
- Sprint 14 entrypoint doc states: “ARTIFACTS ONLY — NO REPLAY_* — NO LIVE SESSION”

---

### S14.1 — Canonical Types + Version Anchors (SSoT wiring)
**Goal:** one source of truth for versions + run anchors used by manifest and records.

**Deliverables**
- `integration/schema_version.py` (SSoT: `INTEGRATION_SCHEMA_VERSION`)
- `integration/kvp_version.py` (SSoT: `KVP_VERSION = "0.1"`)
- `integration/run_anchors.py` (typed structure for: engine_name, engine_version, schema_version, world_id, run_id, seed, tick_rate_hz, time_origin_ms)
- `integration/render_spec.py` (typed structure mirroring `KERNEL_HELLO.render_spec` shape; REQUIRED bounds)

**Acceptance**
- Any export uses these SSoT constants/structures (no ad-hoc strings)
- render_spec cannot be omitted (hard error)

---

### S14.2 — Canonicalization + Quantization Library (JCS-ready surface)
**Goal:** reusable utilities that produce stable bytes for hashing and stable ordering for payloads.

**Deliverables**
- `integration/canonicalize.py`
    - stable array sorting helpers (rooms/agents/items/events)
    - float quantization (Q1E3) helpers (apply everywhere viewer-facing)
- `integration/jcs.py` (or `integration/json_c14n.py`)
    - function: `canonical_json_bytes(obj) -> bytes` (RFC 8785-ish JCS)
    - rule: UTF-8, no BOM, stable number formatting
- `integration/step_hash.py`
    - `compute_step_hash(state_obj) -> str` (sha256 hex of canonical bytes)

**Acceptance**
- Given the same input objects, hashing output is identical across runs/machines
- Unit tests for:
    - quantization (edge cases)
    - ordering (ids)
    - canonical bytes determinism
    - sha output stable

---

### S14.3 — KVP Envelope Writer (Record-level, Independently Decodable)
**Goal:** emit KVP envelope records for `FULL_SNAPSHOT` and `FRAME_DIFF` as artifacts.

**Deliverables**
- `integration/kvp_envelope.py`
    - `make_envelope(msg_type, payload, *, msg_id, sent_at_ms) -> dict`
    - msg_type is authoritative discriminator
- `integration/record_writer.py`
    - `write_record(path, envelope)`: writes one JSON file OR JSONL line (depending on chosen layout)
    - guarantees: record is independently decodable (no outer wrapper assumptions)

**Acceptance**
- Reader can parse any single record without needing a previous record
- Envelope-first dispatch is enforced in tests (no payload-shape dispatch)

---

### S14.4 — Manifest v0.1 (Authoritative Export Index)
**Goal:** `manifest.kvp.json` becomes the only thing the viewer needs to discover everything.

**Deliverables**
- `integration/manifest_schema.py` (typed + validation)
- `integration/manifest_writer.py`
    - writes `manifest.kvp.json`
    - includes:
        - run anchors
        - required `render_spec`
        - tick window (`available_start_tick`, `available_end_tick`)
        - keyframe policy (`keyframe_interval` OR `keyframe_ticks`)
        - channel set for offline scope (effective subscribed channels)
        - record inventory pointers for snapshots + diffs
        - integrity metadata (hashes / hash chain references)
        - overlay pointers (X_*)

**Acceptance**
- Viewer can discover:
    - tick window
    - keyframe ticks
    - where to fetch snapshot for a keyframe tick
    - where to fetch diffs for any tick range
    - integrity verification references
- Validation fails loudly if required fields missing

---

### S14.5 — Export Layout + Indexing Strategy (Normative for Sprint 14)
**Goal:** lock the on-disk layout so WEBVIEW-0002 can implement a “boring loader.”

**Deliverables**
- `docs/kvp_export_layout_v0_1.md` (normative)
- A concrete folder layout, e.g.:
    - `run/manifest.kvp.json`
    - `run/state/snapshots/` (keyframes)
    - `run/state/diffs/` (per-tick diffs, optionally chunked into JSONL + index)
    - `run/overlays/ui_events.*`
    - `run/overlays/psycho.*`
    - `run/index/` (optional: quick lookup tables)
- `integration/index_writer.py`
    - produces tick→file offset maps if using JSONL chunking
    - produces simple “diff ranges” tables per chunk

**Acceptance**
- Layout doc + manifest are sufficient for a viewer implementation
- No implicit conventions (all paths discoverable via manifest)

---

### S14.6 — State Record Exporter (Snapshots + Diffs)
**Goal:** convert integration outputs into KVP-compliant `FULL_SNAPSHOT` + `FRAME_DIFF` artifacts.

**Deliverables**
- `integration/export_state.py`
    - chooses keyframe ticks
    - emits:
        - `FULL_SNAPSHOT` at keyframes
        - `FRAME_DIFF` for each tick transition
    - enforces invariants:
        - schema_version inside each payload
        - canonical ordering + Q1E3 quantization
        - `to_tick = from_tick + 1`
        - `prev_step_hash` chain correctness
- `integration/export_verify.py`
    - replays from exported artifacts and confirms:
        - tick continuity
        - hash chain
        - schema validation

**Acceptance**
- Running verifier on the exported folder passes:
    - can reconstruct state for any tick via snapshot+diffs
    - hash chain matches expected references
    - no missing ticks

---

### S14.7 — Overlay Sidecars (Out-of-Protocol Streams)
**Goal:** export narrative/UI bubbles + psycho topology as separate, deterministic streams.

**Deliverables**
- `integration/overlay_schemas.py` (X_* record schemas)
- `integration/export_overlays.py`
    - `X_UI_EVENT_BATCH` records
    - `X_PSYCHO_FRAME` records
    - sampling rules + tick alignment rules documented
- Manifest pointers for overlays

**Acceptance**
- Overlays never appear inside FULL_SNAPSHOT/FRAME_DIFF
- Viewer can load overlays by tick window using only manifest pointers

---

### S14.8 — Golden Fixture + CI Parity Checks
**Goal:** lock deterministic behavior with a tiny exported run and a strict test suite.

**Deliverables**
- `fixtures/kvp/v0_1/small_run/` (checked-in small export)
- CI tests:
    - manifest schema validation
    - record schema validation
    - replay reconstruction test
    - hash chain verification
    - “no unknown fields in kernel output” lint (schema-minimal)

**Acceptance**
- Fixture export is stable across machines
- Any deviation fails fast (determinism regression protection)

---

### S14.9 — Frontend Contract Pack (Hand-off to WEBVIEW-0002)
**Goal:** give frontend LLM architect a single “contract bundle” so React can go build AAA viewer.

**Deliverables**
- `docs/webview_contract_pack.md` containing:
    - manifest fields to implement first
    - expected record types (FULL_SNAPSHOT/FRAME_DIFF + X_*)
    - seeking algorithm (keyframe → apply diffs)
    - integrity expectations
    - examples (small snippets)
- “Reader reference” pseudo-code for viewer loader (language-agnostic)

**Acceptance**
- Frontend can implement loader + timeline controls without asking backend questions
- All behavior discoverable via manifest + layout doc

---
### Sprint 14 Completion Criteria (One-Line Test)

> Given `path/to/exported_run/manifest.kvp.json`, a viewer can:
> - list tick window + keyframes
> - seek to any tick by loading nearest keyframe snapshot and applying diffs
> - render placeholders using render_spec
> - load overlays by tick
> - verify integrity via manifest-provided references
> - do all of this offline, with no session/transport assumptions