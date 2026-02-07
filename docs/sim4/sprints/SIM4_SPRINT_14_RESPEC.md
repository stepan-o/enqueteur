## Sprint 14 — KVP Replay Export v0.1 (“Viewer-proof offline + React parity”)

**Status update (Feb 2026):** Current implementation differs from this respec:
- `manifest.kvp.json` is a ManifestV0_1 JSON (not a KERNEL_HELLO envelope).
- `FRAME_DIFF` payloads are full-state (no ops list yet).
- Overlays are optional sidecars exported via `integration/export_overlays.py`.

**Goal:** Replace Sprint 14 with a complete, typed, deterministic **offline export + React viewer consumption** path where *every artifact is a KVP envelope message* and the viewer can reuse the same parser/state machine as WS.

**Definition of Done (global)**
- Offline run folder exports **only** `.kvp.json` / `.kvp.jsonl` records (KVP envelope).
- `manifest.kvp.json` is effectively `KERNEL_HELLO` + **stream descriptors** + **render_coordinate_spec** + **integrity metadata**.
- Keyframes are `Envelope<FULL_SNAPSHOT>`.
- Diffs are `Envelope<FRAME_DIFF>` with **explicit ops list** and **hash chaining**.
- Overlays are typed messages (`UI_EVENT_BATCH`, `PSYCHO_FRAME`) keyed by tick.
- Viewer can: load manifest → seek to tick → load keyframe → apply diffs → apply overlays with explicit sampling rules.
- Determinism hooks: canonical ordering + float quantization + stepHash linkage + file hashes (at minimum per chunk).

---

# Sprint 14.0 — Scope lock + schema surface (no behavior change yet)

### 14.0A — Message type inventory + schema decisions
**Tasks**
- Freeze v0.1 message type set for export:
    - existing: `KERNEL_HELLO`, `FULL_SNAPSHOT`, `FRAME_DIFF`
    - new: `ASSETS_MANIFEST` (optional), `REPLAY_INDEX` (recommended), `UI_EVENT_BATCH`, `PSYCHO_FRAME`, `RUN_INTEGRITY` (recommended)
- Decide: `hash_algo` (XXH64/SHA256), quantization precision, chunk sizing defaults (e.g., 1000 ticks).
- Decide: z semantics scope: “draw_depth_hint” only vs stronger guarantees.

**Deliverables**
- `KVP-0001 Replay Export Appendix (v0.1)` (short spec doc)
- `kvp_msg_types_v0_1.ts|rs` enum additions + payload stubs

### 14.0B — Render coordinate contract lock
**Tasks**
- Finalize `render_coordinate_spec` fields and meanings (units, axes, bounds, recommended projection).
- Specify stable draw ordering keys for rooms + agents (exact sort tuple).

**Deliverables**
- `RenderCoordinateSpec` schema + examples
- “No implied iso math” rule written as a MUST

**Exit Criteria**
- Frontend architect signs off that manifest has everything needed to render without guessing.

---

# Sprint 14.1 — Offline export framing (“KVP messages everywhere”)

### 14.1A — Export folder + naming conventions
**Tasks**
- Implement folder layout and naming scheme (run root, keyframes, diffs, overlays, assets).
- Add export config:
    - `chunk_ticks`, `keyframe_period_ticks`, `include_assets_manifest`, `include_run_integrity`, `include_replay_index`.

**Deliverables**
- `export/run_layout.md` (documented file layout)
- `ExportConfig` object + default values

### 14.1B — Manifest as `KERNEL_HELLO` + descriptors
**Tasks**
- Generate `manifest.kvp.json` as envelope with `msg_type=KERNEL_HELLO`.
- Extend `KERNEL_HELLO.payload` to include:
    - `replay_export` descriptors
    - `render_coordinate_spec`
    - `integrity.schema_versions` and `engine_version`
    - tick range + tick rate

**Deliverables**
- `manifest.kvp.json` generator
- Golden manifest example committed

### 14.1C — Keyframes = `Envelope<FULL_SNAPSHOT>`
**Tasks**
- Ensure keyframe JSON uses KVP envelope, not bare snapshot.
- Validate canonicalization and quantization applied before write.
- Store keyframe tick list in manifest.

**Deliverables**
- `keyframes/kf_{tick}.kvp.json` writer
- Golden keyframe sample

**Exit Criteria**
- A replay run produces a valid manifest + at least one keyframe, all as envelopes.

---

# Sprint 14.2 — Diff contract hardening (explicit ops + desync detection)

### 14.2A — Define `FRAME_DIFF.ops[]` contract
**Tasks**
- Replace “replace_lists” style with explicit ops:
    - `UPSERT_ROOM`, `REMOVE_ROOM`
    - `UPSERT_AGENT`, `REMOVE_AGENT`
    - `UPSERT_ITEM`, `REMOVE_ITEM` (if items exist now; otherwise explicitly “not emitted”)
    - `UPSERT_NARRATIVE_FRAGMENT`, `REMOVE_NARRATIVE_FRAGMENT`
    - (optional) `UPSERT_EVENT`, `REMOVE_EVENT` or “event batch replace” as an op
- Add mandatory fields:
    - `from_tick`, `to_tick`
    - `prev_step_hash`, `step_hash`
- Specify ordering rules for ops inside a diff (e.g., removals before upserts? or strict as emitted).

**Deliverables**
- `FrameDiffOps` schema + examples
- Contract doc: “diffs must be applied in order; hash chain must match”

### 14.2B — Implement diff writer as `.kvp.jsonl` chunks
**Tasks**
- Write diff chunks line-delimited: one envelope per line.
- Enforce chunk naming: `diff_{start}_{end}.kvp.jsonl`.
- Add minimal desync metadata: base/prev hash and tick continuity checks.

**Deliverables**
- Diff chunk writer + validator
- Golden diff chunk sample

**Exit Criteria**
- Viewer can apply diffs deterministically from a keyframe without guessing semantics.

---

# Sprint 14.3 — Overlay streams as typed messages (UI + Psycho)

### 14.3A — UI overlay stream: `UI_EVENT_BATCH`
**Tasks**
- Implement `UI_EVENT_BATCH` payload with:
    - `tick`
    - `events[]` each with `event_id`, `priority`, `start_tick`, `end_tick`, target refs (agent/room), text/kind
- Decide whether batches are:
    - emitted every tick with empty list allowed, or
    - emitted only on changes (preferred, but must document sampling rule)

**Deliverables**
- `overlays/ui_events.kvp.jsonl` exporter
- Sampling rule in manifest: “render events where start<=T<=end” + priority ordering

### 14.3B — Psycho overlay stream: `PSYCHO_FRAME`
**Tasks**
- Implement `PSYCHO_FRAME` with:
    - `tick`, `sample_period_ticks`
    - `nodes[]` (per-room metrics)
    - `edges[]` (topology/flow)
    - optional `recommended_range` per metric OR frame min/max
- Document sampling rule: “use latest frame <= T”.

**Deliverables**
- `overlays/psycho_topology.kvp.jsonl` exporter
- Manifest fields: `sample_period_ticks`, `viewer_rule`

**Exit Criteria**
- Overlays are parseable by same envelope parser and align cleanly by tick.

---

# Sprint 14.4 — Assets resolution contract (or explicit NONE)

### 14.4A — `ASSETS_MANIFEST` support
**Tasks**
- Implement optional `assets_manifest.kvp.json` as `ASSETS_MANIFEST`.
- `ref -> url/path + type` mapping + fallback policy.
- If assets absent, manifest must explicitly declare `"assets": {"mode":"NONE" ...}`.

**Deliverables**
- Assets manifest exporter (optional) + manifest integration
- Viewer fallback policy documented (“primitive draw if missing”)

**Exit Criteria**
- Viewer can resolve refs deterministically or safely fall back without runtime errors.

---

# Sprint 14.5 — Index + integrity (make debugging survivable)

### 14.5A — `REPLAY_INDEX`
**Tasks**
- Build index mapping:
    - keyframe ticks → keyframe file path
    - diff chunk ranges → diff file path
    - overlay paths (single files)
- Export as `index.kvp.json` with envelope `REPLAY_INDEX`.

**Deliverables**
- Index exporter + loader sample

### 14.5B — `RUN_INTEGRITY` checksums
**Tasks**
- Hash every chunk file (manifest, index, keyframes, diff chunks, overlays).
- Export `checksums.kvp.json` with `RUN_INTEGRITY`.
- Optionally include keyframe `step_hash` map for fast verification.

**Deliverables**
- Integrity exporter + verifier utility
- CI hook: “golden trace verify” (lightweight)

**Exit Criteria**
- You can detect corruption / wrong-file loads quickly and deterministically.

---

# Sprint 14.6 — React viewer parity path (offline loader + same parser/state machine)

### 14.6A — Unified parser
**Tasks**
- Ensure viewer has a single envelope parser used for:
    - offline `.kvp.json`/`.kvp.jsonl`
    - WS frames (same types)
- Add strict validation:
    - `kvp_version`, `schema_version`, msg_type expected payload
    - tick continuity checks

**Deliverables**
- `kvpCodec.ts` (decode/validate)
- `KvpMessage` discriminated union types for all v0.1 messages

### 14.6B — Offline replay engine
**Tasks**
- Implement:
    - load manifest → load index
    - seek(T): find nearest keyframe ≤ T, load it, apply diffs up to T
    - overlay sampling: UI (interval-based), psycho (latest ≤ T)
- Desync handling in offline mode:
    - if hash chain mismatch: hard error + suggest reload from nearest keyframe

**Deliverables**
- `ReplayController` with seek/scrub
- “Minimal viewer” screen rendering primitives (rooms/agents placeholders OK)

### 14.6C — Draw ordering + coordinate spec enforcement
**Tasks**
- Implement sorting using provided draw keys only.
- Implement projection using manifest’s `recommended_projection` (or treat as hint but no hidden assumptions).
- Camera fit using `world_bounds`.

**Deliverables**
- Deterministic draw order
- Deterministic camera framing on load

**Exit Criteria**
- React viewer can replay exported run deterministically (visuals can be primitive).

---

# Sprint 14.7 — Golden trace + regression harness (lock it in)

### 14.7A — Golden export fixtures
**Tasks**
- Produce 1–2 small “golden runs” checked into repo (or generated deterministically in CI).
- Validate:
    - canonical ordering stable
    - float quantization stable
    - step hash chain stable
    - file hashes stable

**Deliverables**
- `golden/run_small/*` fixture
- CI job: export → compare hashes + parse/seek tests

### 14.7B — Contract tests (kernel + viewer)
**Tasks**
- Kernel-side: schema validation tests per message.
- Viewer-side: parse tests + seek tests (tick 0, mid, end) + overlay sampling tests.

**Deliverables**
- `kvp_contract_tests` suite

**Final Exit Criteria**
- Sprint 14 replaces Sprint 14 entirely: offline export is viewer-proof, React viewer can load/seek/replay using the same KVP message parsing path as streaming.

---

## Suggested execution order (if you need parallelism)
- **Kernel/export track:** 14.1 → 14.2 → 14.3 → 14.4 → 14.5
- **Viewer track:** start 14.6A as soon as 14.0 schemas are locked; 14.6B once 14.1/14.2 samples exist; 14.6C once render spec is stable.
- **QA/CI track:** 14.7 starts once 14.1 produces stable artifacts.
