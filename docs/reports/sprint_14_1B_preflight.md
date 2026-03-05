### Sprint 14.1B — Preflight Verification Report

Role: Junie (Protocol & Export Archaeologist)

Scope: Verify current codebase facts against Assumption Groups A–C. No code added, no refactors. All findings cite concrete files and symbols.

Note on evidence boundaries: The repository contains a Sim5 protocol spec in docs, a TypeScript webview client, and a Sim4 integration/export layer. Verification below references only implemented code, not specification text unless explicitly noted as documentation-only.

**Update (Feb 2026):** The Sim4 integration layer has been replaced with KVP-0001
SSoT modules and a host-level runner. Legacy `render_specs.py`, `frame_builder.py`,
`frame_diff.py`, `exporter.py`, and related schema modules were removed.

---

Section 1 — Confirmed True

- Envelope type exists and is used (frontend, TypeScript)
  - Where: frontend/loopforge-webview/src/kvp/client.ts
  - Symbols:
    - Envelope<TPayload> type (lines ~43–49)
    - KvpClient.sendEnvelope(...) constructs and JSON.stringify’s Envelope (lines ~178–190)
    - KvpClient.onMessage(...) parses Envelope and switches on msg_type (lines ~196–259)
  - Status: ✅ Exists and used consistently within the webview client for sending and receiving messages.

- MsgType includes "KERNEL_HELLO" (frontend, TypeScript)
  - Where: frontend/loopforge-webview/src/kvp/client.ts
  - Symbols:
    - MsgType union type includes "KERNEL_HELLO" (lines ~33–41)
  - Status: ✅ Exists in the same MsgType union used by the client for routing.

- Canonicalization + quantization utilities exist and are used (Sim4 integration)
  - Where: backend/sim4/integration/canonicalize.py (Q1E3 quantization + canonicalization)
  - Usage examples:
    - backend/sim4/integration/export_state.py (canonicalize_state_obj before hashing)
    - backend/sim4/integration/kvp_state_history.py (canonicalize_state_obj before hashing)
  - Status: ✅ Exists and is enforced for KVP export records.

---

Section 2 — Partially True / Risky

- Envelope used consistently across protocol messages (repo-wide)
  - Evidence: The Envelope type is used consistently in the webview client for VIEWER_HELLO, SUBSCRIBE, KERNEL_HELLO reception, FULL_SNAPSHOT/FRAME_DIFF reception. However, no kernel/server-side implementation is present in this repo to validate cross-component consistency.
  - Files: frontend/loopforge-webview/src/kvp/client.ts (sendEnvelope, onMessage)
  - Status: ⚠️ Consistent within frontend; kernel-side usage cannot be verified in this repo.

- KernelHello payload struct exists with required fields
  - Where (frontend only):
    - frontend/loopforge-webview/src/kvp/client.ts → export type KernelHello (lines ~62–71)
    - frontend/loopforge-webview/src/state/worldStore.ts → export type KernelHello (lines ~23–31)
  - Fields present (frontend types): engine_name, engine_version, schema_version, world_id, run_id, seed, tick_rate_hz; time_origin_ms is optional in client.ts type.
  - Serialization path: The client deserializes via JSON.parse in onMessage, and would serialize its own messages via JSON.stringify in sendEnvelope. There is no evidence of kernel-side serialization of KernelHello in this repo.
  - Status: ⚠️ Exists in frontend types and is deserializable via the client’s JSON codec; kernel-side producer is not present here.

- Canonicalization/Quantization for protocol messages
  - Evidence: KVP export paths canonicalize state and compute step_hash before writing envelopes.
  - Files: backend/sim4/integration/canonicalize.py, jcs.py, step_hash.py, export_state.py
  - Status: ✅ Implemented for offline export.

---

Section 3 — False / Missing

- RenderSpec payload (structured KVP contract) and reference from KernelHello
  - Found:
    - RenderSpec SSoT exists: backend/sim4/integration/render_spec.py
    - RenderSpec is required by manifest schema and used in offline export (manifest.kvp.json).
    - Live session helper constructs KernelHello payload with render_spec (backend/sim4/integration/live_session.py).
  - Status: ⚠️ RenderSpec exists and is used in offline exports; kernel-side live transport is scaffolded but no server transport is present in this repo.

- Live handshake path that constructs and sends KernelHello (kernel → viewer)
  - Expected: A server/kernel component constructs a KernelHello payload with real runtime values, including a fully populated render_spec, and sends it inside the same Envelope/codec path as other messages.
  - Found:
    - The webview client constructs and sends ViewerHello and SUBSCRIBE (frontend/loopforge-webview/src/kvp/client.ts: sendViewerHello, sendSubscribe).
    - onMessage handles "KERNEL_HELLO" reception but there is no kernel/server implementation in this repo sending it.
    - No WebSocket server or transport code emitting KernelHello is present in backend.
  - Status: ❌ Does not exist in this repo.

- Offline export framing (KVP-0001 v0.1) implemented
  - Found:
    - backend/sim4/integration/export_state.py writes FULL_SNAPSHOT + FRAME_DIFF envelopes
    - backend/sim4/integration/manifest_schema.py defines ManifestV0_1 (manifest.kvp.json)
    - backend/sim4/host/sim_runner.py orchestrates runtime → snapshot → integration exports
    - Layout: state/snapshots + state/diffs (no artifacts/ sidecar directory)
  - Status: ✅ Implemented (matches docs/kvp_export_layout_v0_1.md).

---

Section 4 — Blocking Ambiguities

- Kernel-side Envelope/codec and KernelHello construction are absent
  - Without kernel/server code in this repo, we cannot verify that KernelHello is constructed with real runtime values, uses the same Envelope+codec, or includes render_spec. This blocks Sprint 14.1B implementation planning.

- RenderSpec definition for KVP-0001 vs Sim4 integration specs
  - RenderSpec SSoT exists and is validated in offline manifests; legacy Room/Agent render specs were removed.

- Offline export framing vs existing exporter
  - Legacy exporter was removed; KVP-0001 export is now the primary implementation.

Stop Rule Assessment (updated)
- Group A: Most items now ✅/⚠️ (RenderSpec + KVP export exist; kernel-side transport still missing).
- Group B: ⚠️ No backend transport emitting KernelHello in this repo.
- Therefore, kernel-side transport remains the primary blocker.

Appendix — File References Index (updated)
- frontend/loopforge-webview/src/kvp/client.ts: Envelope, MsgType, KernelHello type, KvpClient.sendEnvelope, KvpClient.onMessage
- frontend/loopforge-webview/src/state/worldStore.ts: KernelHello type usage and storage
- backend/sim4/integration/canonicalize.py: canonicalization + quantization
- backend/sim4/integration/render_spec.py: RenderSpec SSoT
- backend/sim4/integration/run_anchors.py: RunAnchors SSoT
- backend/sim4/integration/manifest_schema.py: ManifestV0_1
- backend/sim4/integration/export_state.py: FULL_SNAPSHOT/FRAME_DIFF writer
- backend/sim4/host/sim_runner.py: orchestration and artifact export
