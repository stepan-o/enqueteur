# Sprint 14 — KVP Replay Export v0.1 (“Viewer-proof offline + React parity”)
## 14.0A — Message type inventory + schema decisions (LOCK)
### 1) v0.1 Export Message Types (final set)
**Already in KVP-0001**
- `KERNEL_HELLO` (manifest carrier)
- `FULL_SNAPSHOT` (keyframes)
- `FRAME_DIFF` (diff stream)

**Add for offline export parity**
- `REPLAY_INDEX` (single file; maps ticks → files)
- `RUN_INTEGRITY` (single file; checksums + hash algo + optional stepHash map)
- `UI_EVENT_BATCH` (JSONL stream keyed by tick)
- `PSYCHO_FRAME` (JSONL stream keyed by tick)
- `ASSETS_MANIFEST` (optional; ref → url/path mapping)

**Explicitly NOT in v0.1**
- any viewer-only derived render caches
- any engine-specific payloads (Pixi/Godot/Unity etc.)

### 2) File formats (unified)
- `.kvp.json` = exactly **one** KVP envelope per file
- `.kvp.jsonl` = **many** KVP envelopes, one per line (diffs + overlays)

### 3) Hashing + integrity (choose now)
**Hash algorithm:** `SHA-256`
- reason: universal, boring, easy to verify in any language + future-proof

**Integrity scope (v0.1 minimum):**
- manifest, index, each keyframe file, each diff chunk file, each overlay file, assets manifest (if present)
- store: `{ path, bytes, sha256 }[]`

### 4) Quantization (choose now)
**Float quantization policy:** `1e-3` (milliprecision)
- applies to all exported floats: positions, rects, mood/energy scalars, etc.
- rule: quantize in kernel/exporter before hashing and writing

### 5) Chunking defaults (choose now)
- `diff_chunk_ticks = 1000`
- `keyframe_period_ticks = 1000` (keyframe every chunk boundary)
- overlays: single file each (`ui_events.kvp.jsonl`, `psycho.kvp.jsonl`) unless size forces chunking later

### 6) Op semantics scope for diffs (decide the “ops vocabulary” now)
`FRAME_DIFF.payload.ops[]` supports:
- `UPSERT_ROOM`, `REMOVE_ROOM`
- `UPSERT_AGENT`, `REMOVE_AGENT`
- `UPSERT_ITEM`, `REMOVE_ITEM` (optional if items exist; otherwise exporter emits none)
- `UPSERT_EVENT`, `REMOVE_EVENT` (or `EVENT_BATCH_REPLACE` — pick one)
- `UPSERT_NARRATIVE_FRAGMENT`, `REMOVE_NARRATIVE_FRAGMENT`

**Hash chaining requirement**
- `prev_step_hash` required
- `step_hash` required
- viewer must reject if mismatch or tick discontinuity

### 7) Schema versioning policy (explicit)
- `kvp_version = "0.1"` fixed
- single `schema_version` string (current IntegrationSchemaVersion)
- each stream declares `schema_version` in payload; manifest also lists per-stream schema versions
- Items policy: ops exist; exporter emits none until ready ✅