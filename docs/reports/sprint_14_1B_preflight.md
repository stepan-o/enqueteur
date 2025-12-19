### Sprint 14.1B — Preflight Verification Report

Role: Junie (Protocol & Export Archaeologist)

Scope: Verify current codebase facts against Assumption Groups A–C. No code added, no refactors. All findings cite concrete files and symbols.

Note on evidence boundaries: The repository contains a Sim5 protocol spec in docs, a TypeScript webview client, and a Sim4 integration/export layer. Verification below references only implemented code, not specification text unless explicitly noted as documentation-only.

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

- Float quantization utility exists and is used (Sim4 integration)
  - Where: backend/sim4/integration/util/quantize.py
  - Symbol: qf(x: float, step: float = 1e-4) → float
  - Usage examples:
    - backend/sim4/integration/render_specs.py: RoomRenderSpec.__post_init__, AgentRenderSpec.__post_init__
    - backend/sim4/integration/layout_algos.py (multiple qf calls)
    - backend/sim4/integration/psycho_topology.py (qf used for metrics)
  - Status: ✅ Exists and is actively enforced for Sim4 integration DTOs and helpers.

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
  - Evidence: Quantization (qf) is implemented and used in Sim4 integration DTOs (e.g., RoomRenderSpec, AgentRenderSpec). The KVP-0001 spec in docs mandates canonicalization, but implemented canonicalize hooks for KVP messages are not present in runtime code; only documentation shows Rust examples. No enforcement point “before emit/write” for KVP envelopes is found in code.
  - Files: backend/sim4/integration/util/quantize.py; backend/sim4/integration/render_specs.py
  - Status: ⚠️ Quantization exists and is used for Sim4 integration artifacts; enforcement for KVP protocol messages is not found in code.

---

Section 3 — False / Missing

- RenderSpec payload (as a structured KVP contract) and reference from KernelHello
  - Expected: A structured RenderSpec (coord system, projection, etc.) referenced by KernelHello per KVP-0001; KernelHello.render_spec should be present.
  - Found:
    - Sim4-specific render specs exist: backend/sim4/integration/render_specs.py defines RoomRenderSpec and AgentRenderSpec (viewer-facing DTOs), and TickFrame references them (backend/sim4/integration/schema/tick_frame.py lines ~38–41).
    - The frontend KernelHello type (client.ts, worldStore.ts) does not include render_spec.
    - No code links a KVP RenderSpec into KernelHello in this repo.
  - Status: ❌ Does not exist in implemented code.

- Live handshake path that constructs and sends KernelHello (kernel → viewer)
  - Expected: A server/kernel component constructs a KernelHello payload with real runtime values, including a fully populated render_spec, and sends it inside the same Envelope/codec path as other messages.
  - Found:
    - The webview client constructs and sends ViewerHello and SUBSCRIBE (frontend/loopforge-webview/src/kvp/client.ts: sendViewerHello, sendSubscribe).
    - onMessage handles "KERNEL_HELLO" reception but there is no kernel/server implementation in this repo sending it.
    - No WebSocket server or transport code emitting KernelHello is present in backend.
  - Status: ❌ Does not exist in this repo.

- Offline export framing (14.1A) implemented with run-scoped folder and artifacts/
  - Expected (implementation): run_<run_id>/ with manifest.kvp.json, keyframes/, diffs/, artifacts/manifest.json, artifacts/checksums.json created by exporter.
  - Found (current implemented exporter is Sim4-era):
    - backend/sim4/integration/exporter.py writes:
      - manifest.json (at export root)
      - frames/frames.jsonl
      - optional: events/events.jsonl, ui_events/ui_events.jsonl, psycho_topology/psycho_topology.jsonl
    - RunManifest dataclass tracks artifacts as a dict of relative paths (backend/sim4/integration/schema/run_manifest.py), but not under an artifacts/ directory and not following the 14.1A KVP envelope scheme.
    - No writer for artifacts/manifest.json or artifacts/checksums.json exists.
  - Status: ❌ Does not exist (implemented structure differs; no artifacts/ folder or KVP envelope files).

---

Section 4 — Blocking Ambiguities

- Kernel-side Envelope/codec and KernelHello construction are absent
  - Without kernel/server code in this repo, we cannot verify that KernelHello is constructed with real runtime values, uses the same Envelope+codec, or includes render_spec. This blocks Sprint 14.1B implementation planning.

- RenderSpec definition for KVP-0001 vs Sim4 integration specs
  - The only implemented "render spec" code is for Sim4 integration (RoomRenderSpec, AgentRenderSpec) and is not wired into KernelHello. It is unclear whether Sim5 intends a different, consolidated RenderSpec (coord system, projection, z layers) per KVP-0001. This gap affects manifest generation and handshake completeness.

- Offline export framing (14.1A) vs existing Sim4 exporter
  - The implemented exporter writes Sim4-style artifacts (manifest.json + frames.jsonl) and not KVP envelopes or the artifacts/ subfolder specified for 14.1A. It’s ambiguous whether 14.1A expects a new exporter or adaptation of the existing one; in any case, the implementation does not exist here.

Stop Rule Assessment
- Group A: Multiple items are ❌/⚠️ (RenderSpec linkage and kernel-side implementations missing).
- Group B: ❌ No kernel-side KernelHello construction present.
- Therefore, Sprint 14.1B must pause until clarifications and/or kernel-side code are available in this repository.

Appendix — File References Index
- frontend/loopforge-webview/src/kvp/client.ts: Envelope, MsgType, KernelHello type, KvpClient.sendEnvelope, KvpClient.onMessage
- frontend/loopforge-webview/src/state/worldStore.ts: KernelHello type usage and storage
- backend/sim4/integration/util/quantize.py: qf quantization utility
- backend/sim4/integration/render_specs.py: RoomRenderSpec, AgentRenderSpec using qf
- backend/sim4/integration/schema/tick_frame.py: room_render_specs and agent_render_specs presence
- backend/sim4/integration/schema/run_manifest.py: RunManifest with artifacts dict
- backend/sim4/integration/exporter.py: export_run writing manifest.json and frames.jsonl (and optional sidecars)
