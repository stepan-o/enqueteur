KVP Export Layout v0.1 — NORMATIVE

Required scope lock statement:

ARTIFACTS ONLY — NO REPLAY_* — NO LIVE SESSION

Purpose
- This document locks the v0.1 on-disk export layout for Sim4 Sprint 14.
- It is normative. Viewers and tools MUST follow it exactly. Do not infer or guess.

Authoritative discovery
- manifest.kvp.json is authoritative.
- The viewer MUST NOT infer paths by convention; it MUST follow pointers declared in the manifest.
- All paths are relative to the run root and suitable for disk or static HTTP hosting.

Required top-level files/dirs
- manifest.kvp.json (REQUIRED, authoritative index)
- state/
  - state/snapshots/
  - state/diffs/
- overlays/ (optional but reserved)
- index/ (optional; not used in v0.1 Mode A)

Canonical file naming conventions (normative)
- Snapshots (keyframes):
  - state/snapshots/tick_{T:010d}.kvp.json
  - Each file contains exactly one KVP envelope with msg_type = FULL_SNAPSHOT.

- Diffs — Mode A (v0.1 default): per-tick diff files
  - state/diffs/from_{F:010d}_to_{T:010d}.kvp.json where T = F + 1
  - Each file contains exactly one KVP envelope with msg_type = FRAME_DIFF.

Normative statements
- Every snapshot/diff record MUST be independently decodable as a standalone KVP envelope file.
- Paths MUST be referenced from manifest.kvp.json using RecordPointer.rel_path; no implicit directory scans.

Overlay conventions
- overlays/ui_events.jsonl (recommended)
- overlays/psycho_frames.jsonl (recommended)
- Overlays are sidecars (X_* streams). They are NOT included inside FULL_SNAPSHOT/FRAME_DIFF payloads.

Index conventions (v0.1 Mode A)
- Indexes are NOT used in v0.1 Mode A. The viewer discovers everything from the manifest pointers.
- If a future version adopts JSONL chunking, index/ would contain JSON index files mapping from_tick to byte_offset with UTF‑8 (no BOM) and sha256 integrity; out of scope for v0.1.

Manifest binding (normative)
- The manifest is the only discovery surface. The viewer MUST NOT infer paths by filename patterns.
- All important paths are discoverable from manifest pointers:
  - run identity and determinism: run_anchors
  - render contract: render_spec
  - tick window: available_start_tick / available_end_tick
  - keyframe policy: keyframe_interval XOR keyframe_ticks
  - where to fetch snapshots/diffs: snapshots map and diffs inventory
  - integrity references: integrity map (hash_alg = "SHA-256")
  - overlays: overlays map (optional)
- Layout hints SHOULD be populated in manifest.layout to remove ambiguity:
  - records_root = "."
  - snapshots_dir = "state/snapshots"
  - diffs_dir = "state/diffs"
  - overlays_dir = "overlays" (if used)
  - index_dir = "index" (if used)
  - diff_storage = "PER_TICK_FILES"

Compliance reminder
- ARTIFACTS ONLY — NO REPLAY_* — NO LIVE SESSION
- No WebSockets, no handshake/subscribe lifecycle, no REPLAY_* control messages, no session simulation.

Implementation note
- This layout matches the current exporter in `backend/sim4/integration/export_state.py`
  and host orchestration in `backend/sim4/host/sim_runner.py`.
