# Sprint 14 — KVP Replay Export (Offline, Viewer-First)

## 🔒 Scope Lock: REPLAY / ARTIFACT MODE ONLY

**Sprint 14 does NOT implement a live kernel, server, or transport.**  
There is **no WebSocket, no handshake runtime, and no streaming kernel process** in this sprint.

Sprint 14 operates **entirely on recorded simulation output** produced by Sprints 9–13.

> Think of Sprint 14 as **“the kernel after the fact”**:  
> it serializes already-computed integration data into **KVP-0001–compliant replay artifacts** so viewers can load, scrub, rewind, and render deterministically — without talking to a running simulation.

This sprint exists to make the simulation **viewer-consumable**, not to run it.

## 🎯 Primary Goal (Why Sprint 14 Exists)

By the end of Sprint 14:

- A completed simulation run can be **exported to disk**
- A frontend viewer (WEBVIEW-0002) can:
    - load the run **offline**
    - seek to any tick
    - apply snapshots + diffs deterministically
    - render 2.5D / isometric placeholders
    - display narrative bubbles
    - overlay psycho-topology data
- All data is shaped, ordered, quantized, and packaged **exactly according to KVP-0001**
- The same artifacts will later be usable for:
    - live replay
    - debugging
    - QA
    - future streaming transports

No viewer should need **any knowledge of Sim4/Sim5 internals** to consume these artifacts.

## 🧠 Mental Model (Read This First)
```text
[ Simulation Run (already finished) ]
                 ↓
[ Integration Outputs (Sprints 9–13) ]
     - TickFrame
     - RoomRenderSpec / AgentRenderSpec
     - UI bubble events
     - PsychoTopology frames
                 ↓
[ Sprint 14: Export + Framing ]
     - Wrap state in KVP envelopes
     - Write deterministic file layout
     - Emit replay artifacts
                 ↓
[ Viewer (WEBVIEW-0002) ]
     - Loads from disk / HTTP
     - No kernel connection
     - No runtime authority
```

**Sprint 14 does not change simulation behavior.**  
It only changes **how results are packaged and exposed**.

## 📡 Relationship to KVP-0001 (Important)

Sprint 14 is **fully aligned with KVP-0001**, but only uses the **REPLAY / ARTIFACT** side of the protocol.

Key clarifications:

- `KERNEL_HELLO`
    - Emitted as a **serialized artifact** (`manifest.kvp.json`)
    - Not sent over a socket
    - Represents authoritative run metadata + render contract

- `FULL_SNAPSHOT`, `FRAME_DIFF`
    - Emitted as **offline KVP envelopes**
    - Identical shape to live messages
    - Stored in files instead of streamed

- **No live handshake or subscription**
    - `VIEWER_HELLO`, `SUBSCRIBE`, etc. are **out of scope**
    - Viewer loads artifacts directly

This ensures **parity**:
- replay == live, just delayed and file-backed

## 🧩 What Sprint 14 Builds (and What It Does Not)

### Sprint 14 BUILDS:
- Deterministic export layout
- KVP-wrapped snapshots and diffs
- Artifact sidecars (indexes, checksums, overlays)
- A viewer-ready replay surface for WEBVIEW-0002

### Sprint 14 DOES NOT BUILD:
- A running kernel
- A server or transport
- Live streaming logic
- Viewer UI
- Rendering code
- Simulation logic

If something feels like “runtime behavior,” it does not belong here.

## 🧪 Why This Matters for the Frontend Architect

For **WEBVIEW-0002**, Sprint 14 guarantees:

- A stable, boring, deterministic input surface
- Zero dependency on kernel language or runtime
- Ability to:
    - implement timeline controls
    - debug replay deterministically
    - iterate on rendering freely
- Confidence that:
    - what works in replay will work live later

The frontend architect should be able to build the entire viewer **without asking the backend anything**.

## ✅ Success Definition

Sprint 14 is successful when:

> A frontend engineer can point a viewer at an exported run folder and say  
> **“This is all I need.”**

No sockets.  
No questions.  
No ambiguity.