# Offline Replay Export — Folder Layout and Naming (Sprint 14.1A)

Purpose
- Define a deterministic, grep-friendly folder layout for offline exports that cleanly separates KVP protocol messages from non-protocol sidecar artifacts.
- Keep “KVP everywhere” for simulation state while avoiding protocol pollution for indexes, checksums, and overlays.

Locked Constraints
- KVP-0001 v0.1 is authoritative and unchanged by this document.
- Only simulation state is represented as KVP envelopes.
- Everything else (indexes, checksums, overlays, UI hints) is a sidecar artifact.
- This sprint is documentation and config defaults only. No runtime/exporter implementation.

Canonical Folder Layout

run_<run_id>/
  manifest.kvp.json          # KVP envelope: KERNEL_HELLO (protocol)
  keyframes/                 # KVP envelopes: FULL_SNAPSHOT
    kf_{tick}.kvp.json
  diffs/                     # KVP envelopes: FRAME_DIFF
    df_{from_tick}_{to_tick}.kvp.jsonl   # or chunked .kvp.jsonl by export policy
  artifacts/                 # Non-protocol sidecars only
    manifest.json            # Sidecar index (non-KVP)
    checksums.json           # Integrity hashes (non-KVP)
    overlays_ui.jsonl        # Optional, UI-only overlays (viewer-facing)
    overlays_psycho.jsonl    # Optional, psycho-topology overlays
  assets/                    # Optional assets block (if exported)
    assets_manifest.json
    textures/
    audio/

Rules
- KVP messages live only at top-level (manifest.kvp.json) and in keyframes/ and diffs/.
- artifacts/ contains anything that is NOT a KVP envelope. Do not nest protocol data inside artifacts/.
- Naming must be stable, boring, and grep-friendly: predictable prefixes (kf_, df_), lowercase, snake or simple kebab not required, and explicit extensions .kvp.json or .kvp.jsonl for envelopes.
- Diffs may be chunked as .kvp.jsonl files; each line is one KVP envelope record.
- Keyframes are discrete .kvp.json files, one envelope per file.

KVP vs Artifact Classification

| Path                               | Classification | Notes                                               |
|------------------------------------|----------------|-----------------------------------------------------|
| manifest.kvp.json                  | KVP protocol   | Envelope<KERNEL_HELLO> with export descriptors.     |
| keyframes/kf_{tick}.kvp.json       | KVP protocol   | Envelope<FULL_SNAPSHOT>.                            |
| diffs/df_{from}_{to}.kvp.jsonl     | KVP protocol   | Each line: Envelope<FRAME_DIFF>.                    |
| artifacts/manifest.json            | Artifact       | Sidecar replay index and helpers; not protocol.     |
| artifacts/checksums.json           | Artifact       | Integrity hashes of files/chunks; not protocol.     |
| artifacts/overlays_ui.jsonl        | Artifact       | UI-only overlays; viewer convenience, not protocol. |
| artifacts/overlays_psycho.jsonl    | Artifact       | Psycho-topology overlays; analysis-only.            |
| assets/** and assets_manifest.json | Artifact       | Asset packaging, not protocol.                      |

Why overlays and indexes are artifacts (not protocol)
- Replay indexes (seek tables, file maps) are derived conveniences that do not affect simulation truth; they change with packaging strategies and are not part of the KVP message contract.
- UI and psycho overlays are viewer- or analysis-facing annotations; they do not change simulation state and should not constrain engine protocol. Keeping them as sidecars allows iteration without protocol churn.

ExportConfig (concept only; defaults, no code)

The following conceptual configuration controls exporters. This sprint defines defaults only.

- chunk_ticks: 1000
  - Default max ticks per diff chunk (.kvp.jsonl). May be ignored by implementations that do not chunk.
- keyframe_period_ticks: 10000
  - Default spacing between FULL_SNAPSHOT keyframes.
- include_assets_manifest: false
  - If true, write assets/assets_manifest.json and include referenced assets paths.
- include_run_integrity: true
  - If true, write artifacts/checksums.json with integrity hashes for key files/chunks.
- include_replay_index: true
  - If true, write artifacts/manifest.json (sidecar index for seek/locate convenience).
- include_ui_overlays (optional): false
  - If true, emit artifacts/overlays_ui.jsonl.
- include_psycho_overlays (optional): false
  - If true, emit artifacts/overlays_psycho.jsonl.

Notes on naming and stability
- Keyframes use kf_{tick}.kvp.json where tick is zero-padded only if a tool requires fixed width. Do not include timestamps; tick is sufficient and deterministic.
- Diff chunks use df_{from_tick}_{to_tick}.kvp.jsonl for clarity and grep-ability. If chunks are rolling, to_tick reflects the last included diff’s to_tick.
- Use ASCII-only names, no spaces, no locale-specific characters.

Non-goals (explicit)
- Do not modify KVP-0001 or add protocol fields.
- Do not write exporter, runtime, or serialization code.
- Do not invent new message types or implement replay logic.
- If an element feels like “protocol,” classify it as an artifact unless already defined in KVP-0001 v0.1.

Outcome
- A reader can understand the export layout without reading any code.
- Engineers can reliably locate: snapshots (keyframes/), diffs (diffs/), overlays and indexes (artifacts/), and integrity info (artifacts/checksums.json).
