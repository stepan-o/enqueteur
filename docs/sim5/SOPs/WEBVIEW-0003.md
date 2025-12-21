WEBVIEW-0003 — Offline Viewer Contract (Sprint 14 handoff)

Tagline: ARTIFACTS ONLY — NO REPLAY_* — NO LIVE SESSION

Purpose
- Viewer-first, implementation-oriented contract so a React/WebView architect can ship WEBVIEW-0002 offline mode without backend questions.
- Grounded in Sprint 14 exports only (manifest + KVP-enveloped records + overlay sidecars).
- Repeat after me: manifest.kvp.json is authoritative.

---

1. What the viewer gets
- One run folder. Entry point is manifest.kvp.json (authoritative discovery surface).
- State records:
  - FULL_SNAPSHOT files (keyframe snapshots)
  - FRAME_DIFF files (per-tick from→to=from+1)
- Overlay sidecars (JSONL, each line is a KVP envelope):
  - X_UI_EVENT_BATCH
  - X_PSYCHO_FRAME
- Optional parity file for CI: fixture_hashes.json (helpful for dev “strict mode”, not required for runtime).
- All files are UTF‑8, no BOM, compact JSON.
- Paths are relative to the run root and suitable for disk or static HTTP.

Also see the checked-in example: fixtures/kvp/v0_1/small_run/

---

2. Folder layout (v0.1)
- Minimal required structure (see docs/kvp_export_layout_v0_1.md):
  - manifest.kvp.json (authoritative index)
  - state/
    - state/snapshots/
    - state/diffs/
  - overlays/ (UI events, psycho frames)
- Hard rule: the viewer MUST NOT guess paths. It must follow pointers from manifest.kvp.json. In other words, manifest.kvp.json is authoritative.

---

3. Manifest: fields to implement first
Build order checklist (names match schema):
- run_anchors: engine_name, engine_version, schema_version, world_id, run_id, seed, tick_rate_hz, time_origin_ms
- render_spec (REQUIRED)
- available_start_tick, available_end_tick (tick window)
- Keyframe policy: exactly one of keyframe_interval or keyframe_ticks
- snapshots: tick -> RecordPointer (path to FULL_SNAPSHOT)
- diffs: inventory pointers that cover every from_tick in [start, end)
- overlays: map of overlay type -> OverlayPointer (paths + format)
- integrity: records_sha256 map (or inline content hashes)

Field → What UI needs it for
- run_anchors → Show run identity; derive ms per tick; clock displays
- render_spec → Configure camera/coord system; draw order; Z-layer stability
- available_*_tick → Timeline bounds; validate seeks
- keyframe_* → Compute nearest keyframe ≤ target
- snapshots → Locate snapshot file for a keyframe tick
- diffs → Locate required per-tick diffs to reach target
- overlays → Fetch UI/psycho sidecars for the same tick window
- integrity → Optional “strict mode” file parity checks (debug/dev toggle)

---

4. Record envelope contract (all artifacts)
- Every artifact record is a single JSON object with keys:
  - kvp_version, msg_type, msg_id, sent_at_ms, payload
- Envelope-first dispatch: viewer decides handler using msg_type only. Do not inspect payload shape to determine type.
- Determinism: msg_id is deterministic; sent_at_ms = 0 (do not rely on wall time).

Minimal example envelope (generic):
{
  "kvp_version": "0.1",
  "msg_type": "FULL_SNAPSHOT",
  "msg_id": "uuid-v5",
  "sent_at_ms": 0,
  "payload": { /* schema-specific */ }
}

---

5. Record types + payload expectations
- FULL_SNAPSHOT
  - Payload contains schema_version, tick, state, step_hash
  - “Complete baseline”: a viewer-ready state object after canonicalization
- FRAME_DIFF
  - Payload contains schema_version, from_tick, to_tick (to_tick = from_tick + 1), prev_step_hash, state (v0.1 pragmatic diff), step_hash
  - Hash chain: prev_step_hash must match the previous step (snapshot hash at keyframe, then prior diff)
  - Apply concept: reconstruct by sequentially replacing state with payload.state (no kernel needed)
- X_UI_EVENT_BATCH (JSONL)
  - Inclusive window: start_tick, end_tick
  - events: list of {tick, event_id, kind, data}; sorted by (tick, event_id)
  - Use in UI: timeline overlays, narrative bubbles
- X_PSYCHO_FRAME (JSONL)
  - tick; nodes; edges
  - nodes sorted by id; edges sorted by (src_id, dst_id, kind)
  - Use in UI: psycho topology layer(s)

Hard rule: overlays MUST NOT appear inside FULL_SNAPSHOT or FRAME_DIFF payloads.

---

6. Seeking algorithm (viewer loader)
Pseudocode (language-agnostic):
1) m = load(manifest.kvp.json)
2) assert target_tick in [m.available_start_tick, m.available_end_tick]
3) kf = nearest_keyframe_leq(target_tick, from m.keyframe_ticks or derived from m.keyframe_interval)
4) snap_ptr = m.snapshots[kf]; snap_env = fetch_json(snap_ptr.rel_path)
5) state = snap_env.payload.state; prev_hash = snap_env.payload.step_hash
6) for t in range(kf, target_tick):
     diff_ptr = m.diffs.diffs_by_from_tick[t]
     diff_env = fetch_json(diff_ptr.rel_path)
     assert diff_env.payload.to_tick == t+1
     if strict_mode: assert diff_env.payload.prev_step_hash == prev_hash
     state = diff_env.payload.state
     prev_hash = diff_env.payload.step_hash
7) render(state)

Failure modes (error out):
- Missing snapshot/diff pointer or file
- Keyframe policy not resolvable
- to_tick != from_tick+1 or broken hash chain in strict mode

---

7. Integrity expectations (optional but supported)
- Manifest integrity (records_sha256) can verify file bytes in a dev/QA “strict mode”.
- Step-hash chain (snapshot/diff payloads) can be validated during seek; recommended as a toggle for debug builds.
- Recommendation: default to fast mode in production; enable strict mode in QA/devtools.

---

8. Examples from the golden fixture (small snippets)
All paths relative to fixtures/kvp/v0_1/small_run/.

Manifest snippet (tick window + one pointer each):
{
  "available_start_tick": 0,
  "available_end_tick": 3,
  "keyframe_ticks": [0, 2],
  "snapshots": {
    "0": {"rel_path": "state/snapshots/tick_0000000000.kvp.json", "msg_type":"FULL_SNAPSHOT"}
  },
  "diffs": {
    "diffs_by_from_tick": {"0": {"rel_path": "state/diffs/from_0000000000_to_0000000001.kvp.json", "msg_type":"FRAME_DIFF"}}
  },
  "overlays": {"X_UI_EVENT_BATCH": {"rel_path": "overlays/ui_events.jsonl", "format": "JSONL"}}
}

Snapshot envelope snippet:
{
  "msg_type": "FULL_SNAPSHOT",
  "payload": {"schema_version": "1", "tick": 0, "state": {"tick": 0}, "step_hash": "…"}
}

Diff envelope snippet:
{
  "msg_type": "FRAME_DIFF",
  "payload": {"schema_version": "1", "from_tick": 0, "to_tick": 1, "prev_step_hash": "…", "state": {"tick": 1}, "step_hash": "…"}
}

Overlay JSONL line snippet (UI events):
{"msg_type":"X_UI_EVENT_BATCH","payload":{"schema_version":"1","start_tick":0,"end_tick":1,"events":[{"tick":0,"event_id":"a","kind":"hover","data":{"x":1.234}}]}}

---

9. Frontend checklist: WEBVIEW-0002 implementation order
1) Manifest loader (JSON fetcher; validation to minimal fields)
2) Record fetcher (JSON + JSONL line streaming)
3) State reconstruction (snapshot + per-tick diffs; envelope-first dispatch)
4) Timeline controls (seek/scrub; clamp to available_* ticks)
5) Overlay layers (UI events + psycho topology)
6) Strict mode integrity toggle (records_sha256 + step_hash chain)
7) Devtools panel: show current tick, nearest keyframe, diff count applied

---

Don’t do this (Sprint 14 scope lock)
- No WebSockets, sockets, or transport code
- No HELLO/SUBSCRIBE or any handshake/session lifecycle
- No REPLAY_* control messages (REPLAY_BEGIN/SEEK/READY/etc.)
- No server-mediated replay
- No “offline simulated session”

Repeat the mantra: ARTIFACTS ONLY — NO REPLAY_* — NO LIVE SESSION. And remember: manifest.kvp.json is authoritative.
