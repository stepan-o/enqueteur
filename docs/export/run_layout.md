# Offline Replay Export — Folder Layout (Current Implementation)

Purpose
- Document the **implemented** KVP-0001 v0.1 export layout used by Sim4.
- Make it easy for viewers/tools to locate snapshots/diffs via the manifest.

Locked Constraints
- KVP-0001 v0.1 is authoritative.
- `manifest.kvp.json` is the only discovery surface; viewers must follow manifest pointers.
- Snapshots/diffs are written as standalone KVP envelopes.
- Overlays are optional sidecars (non-protocol).

Canonical Folder Layout (implemented)

run_root/
  manifest.kvp.json                    # ManifestV0_1 (SSoT; NOT an envelope)
  state/
    snapshots/
      tick_{T:010d}.kvp.json           # Envelope<FULL_SNAPSHOT>
    diffs/
      from_{F:010d}_to_{F+1:010d}.kvp.json  # Envelope<FRAME_DIFF>
  overlays/                            # Optional JSONL overlays
    ui_events_{start}_{end}.jsonl
    psycho_frames.jsonl

Rules
- All snapshot/diff paths are referenced from `manifest.kvp.json` via `RecordPointer.rel_path`.
- No implicit directory scanning by viewers.
- File names are stable and deterministic; tick numbers are zero-padded to 10 digits.
- Overlays are optional and referenced from `manifest.kvp.json` via `overlays`.

KVP vs Artifact Classification

| Path                                                | Classification | Notes                                              |
|-----------------------------------------------------|----------------|----------------------------------------------------|
| manifest.kvp.json                                   | Manifest SSoT  | ManifestV0_1 JSON; not an envelope                 |
| state/snapshots/tick_{T:010d}.kvp.json              | KVP protocol   | Envelope<FULL_SNAPSHOT>                            |
| state/diffs/from_{F:010d}_to_{F+1:010d}.kvp.json    | KVP protocol   | Envelope<FRAME_DIFF>                               |
| overlays/*.jsonl                                    | Artifact       | Optional UI/psycho overlays (non-protocol)         |

Implementation Notes
- Exporter: `backend/sim4/integration/export_state.py`
- Manifest schema: `backend/sim4/integration/manifest_schema.py`
- Host orchestration: `backend/sim4/host/sim_runner.py`
- Canonicalization + hashing: `backend/sim4/integration/canonicalize.py`, `jcs.py`, `step_hash.py`

Non-goals
- No assets packaging.
- No artifacts/manifest.json sidecar.
- No JSONL chunked diffs (v0.1 uses per-tick files).
