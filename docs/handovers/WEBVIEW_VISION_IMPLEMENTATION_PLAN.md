# WebView Vision Implementation Plan (Director Mode → Interactive Show)

Last updated: 2026-02-08

This document translates the UX vision into concrete implementation steps across the backend and frontend, with explicit file/module touchpoints. It is written to preserve KVP-0001 determinism and SOP-100/SOP-200 separation while turning the current offline replay into a watchable, interactive product.

---

## 1) Current Baseline (Already Wired End-to-End)

These are working today and can be used as foundation:

- Deterministic Sim4 → KVP-0001 snapshots/diffs → Pixi WebView offline replay.
- Rooms with bounds and floors defined in backend and rendered in frontend.
- Cutaway interaction (click room) and floor switching.
- Offline demo artifacts are generated and loaded locally.

Key files:
- Layout + bounds: `backend/sim4/world/loopforge_layout.py`
- World context: `backend/sim4/world/context.py`
- Offline export runner: `scripts/run_sim4_kvp_demo.py`
- Offline export plumbing: `backend/sim4/host/sim_runner.py`
- RenderSpec defaults: `backend/sim4/host/kvp_defaults.py`
- Offline loader: `frontend/loopforge-webview/src/kvp/offline.ts`
- Store: `frontend/loopforge-webview/src/state/worldStore.ts`
- Renderer: `frontend/loopforge-webview/src/render/pixiScene.ts`
- HUD: `frontend/loopforge-webview/src/ui/hud.ts`
- Dev controls: `frontend/loopforge-webview/src/ui/devControls.ts`

---

## 2) The Vision Gaps (What’s Missing Today)

To hit the “Watch → Notice → Poke → Observe → Share” loop, the following gaps need to be closed:

- No event ticker or room pings tied to `events` channel.
- Room tension is in data (`tension_tier`) but not visualized as a signal.
- Agents lack readability (mood, speaking, intent).
- No camera modes beyond free (no follow or auto-director).
- No overlay pipeline in viewer (UI events + psycho frames exist server-side, but are not loaded client-side).
- Live INPUT_COMMAND is not wired in transport or runtime (live session accepts hello/subscribe only).
- Timeline controls lack pause/scrub/speed, and no seek-to-keyframe logic.
- Items are currently suppressed in renderer.
- Shareable run/tick links are not generated or parsed.

---

## 3) Architectural Rule (Non-Negotiable)

Maintain three independent stores to preserve determinism and clarity:

- Kernel state store (rooms/agents/items/events) from snapshots + diffs only.
- Overlay store (ui_events, psycho_frames) from overlay files/streams only.
- Viewer state store (camera, selection, filters, follow mode) UI-only.

Where this should live:
- Kernel state: `frontend/loopforge-webview/src/state/worldStore.ts`
- Overlay state: new `frontend/loopforge-webview/src/state/overlayStore.ts`
- Viewer state: new `frontend/loopforge-webview/src/state/viewerStore.ts`

---

## 4) Milestone A — Watchable Demo (Offline-Only)

Goal: make the sim feel alive and readable in 5–10 seconds without any live inputs.

### A1) Event Ticker + Room Pings

- Add a right-side feed in HUD showing recent world events.
- Add room halo/ping effect for 1–2 seconds on event.

Files:
- `frontend/loopforge-webview/src/state/worldStore.ts` to expose events cleanly.
- `frontend/loopforge-webview/src/ui/hud.ts` to render ticker.
- `frontend/loopforge-webview/src/render/pixiScene.ts` to render ping FX.

### A2) Tension-Driven Room Shading

- Use `room.tension_tier` to tint top face and add subtle pulse.

Files:
- `frontend/loopforge-webview/src/render/pixiScene.ts` in room shading (`roomColors`).

### A3) Agent Readability

- Mood ring color (overlay or state field).
- Speaking icon/bubble (overlay-driven).
- Hover tooltip with name + basic status.

Files:
- `frontend/loopforge-webview/src/render/pixiScene.ts`
- `frontend/loopforge-webview/src/ui/hud.ts`

### A4) Camera Modes

- Free (current).
- Follow agent (smooth pan to selected agent).
- Auto-director (switch to most “interesting” room on a timer).

Files:
- `frontend/loopforge-webview/src/render/pixiScene.ts` camera transforms.
- `frontend/loopforge-webview/src/ui/devControls.ts` or new control panel.
- `frontend/loopforge-webview/src/app/boot.ts` to wire controls.

---

## 5) Milestone B — Overlay Story Layer (Offline)

Goal: add “story signals” without touching deterministic kernel state.

### B1) Enable overlay export in offline artifacts

- The backend already supports overlay export in `SimRunner._write_offline_artifacts`.
- Provide `ui_events` and `psycho_frames` to `OfflineExportConfig`.

Files:
- `backend/sim4/host/sim_runner.py` (already supports overlays).
- `backend/sim4/integration/export_overlays.py` + `overlay_schemas.py`.
- `scripts/run_sim4_kvp_demo.py` to pass overlay batches.

### B2) Add overlay loader + store on the viewer

- Load `overlays/ui_events.jsonl` and `overlays/psycho_frames.jsonl` from manifest.
- Index overlays by tick for fast apply during playback.

Files:
- `frontend/loopforge-webview/src/kvp/offline.ts` to load overlays.
- New: `frontend/loopforge-webview/src/state/overlayStore.ts`.
- `frontend/loopforge-webview/src/ui/hud.ts` to render overlay feed.
- `frontend/loopforge-webview/src/render/pixiScene.ts` to render speech/thought FX.

---

## 6) Milestone C — Interactive Live (Deterministic Nudges)

Goal: allow the viewer to “poke” the sim without breaking determinism.

### C1) Live transport capable of INPUT_COMMAND

- Live envelope schema already supports `INPUT_COMMAND` and ACK/REJECT.
- Live session state machine currently only handles VIEWER_HELLO, SUBSCRIBE, PING.

Backend work needed:
- Extend `backend/sim4/integration/live_session.py` to accept and route INPUT_COMMAND.
- Implement a transport server that owns a `LiveSession` and forwards commands into the runtime.

### C2) Deterministic command handling in runtime

- `backend/sim4/runtime/command_bus.py` already batches commands deterministically.
- Need a receiver that maps input commands to `WorldCommand` or ECS commands.
- Likely add a small input → world command translator in runtime or host layer.

### C3) Frontend command UX

- Add a room context menu with 3 nudges.
- Send INPUT_COMMAND over live websocket.
- Display command accepted/rejected toast.

Files:
- `frontend/loopforge-webview/src/kvp/client.ts`
- `frontend/loopforge-webview/src/ui/hud.ts`
- `frontend/loopforge-webview/src/ui/devControls.ts`

---

## 7) Milestone D — Shareable Runs + Playback UX

Goal: turn the viewer into a sharable product.

### D1) Playback controls

- Play / Pause
- Scrub bar with tick markers
- Speed controls 0.25× / 1× / 2× / 4×
- Seek uses keyframes then diffs

Files:
- `frontend/loopforge-webview/src/kvp/offline.ts` (seek logic)
- `frontend/loopforge-webview/src/ui/hud.ts` or a new playback UI panel

### D2) URL state

- `?run=...&tick=...&follow=agent:3`
- State should be read on boot and applied to viewer store

Files:
- `frontend/loopforge-webview/src/app/boot.ts`
- New viewer store for camera + selection

---

## 8) Items and Props (Phase-In Approach)

Items are already in KVP state but currently hidden.

Phased plan:
- Phase 1: static props only (rendered allowlist).
- Phase 2: stateful props (broken/idle).
- Phase 3: story props (triggered by events).

Files:
- `frontend/loopforge-webview/src/render/pixiScene.ts` (items rendering is currently disabled).
- Allowlist filter should be in renderer or a new `itemPresentation.ts` helper.

---

## 9) Concrete “What We Need to Build” Checklist

This is the minimal list to hit the UX architect’s vision with realistic scope:

1. Add overlay store + loader + UI feed.
2. Render event pings and tension shading.
3. Add agent readability (mood ring + speech bubble via overlays).
4. Add camera modes: free, follow, auto-director.
5. Add playback controls: pause, speed, scrub, seek-to-keyframe.
6. Wire live INPUT_COMMAND handling (transport + runtime adapter).
7. Add room nudge UI and command ACK/REJECT.
8. Re-enable items with allowlist filter.
9. Add URL state for shareable ticks and follow modes.

---

## 10) Immediate Next Steps (If Starting Tomorrow)

If we start tomorrow, the fastest “watchable” win is frontend-first:

1. Event ticker + room ping FX.
2. Tension shading.
3. Follow-agent camera.
4. Overlay loader (consume existing fixture overlays).

Backend can follow once the viewer demands richer signals:

1. Add overlay generation to demo artifacts.
2. Add deterministic live command handling.

---

## 11) Notes on Determinism + KVP Sovereignty

All interactivity must remain in one of two categories:

- Viewer-only: camera, filters, cutaways, overlays (non-kernel).
- Kernel-validated: input commands that are accepted, applied, and replayed by the kernel.

Avoid any direct UI-driven mutation of kernel state in the client.

---

## 12) Key Files Index (Fast Lookup)

Backend:
- `backend/sim4/world/loopforge_layout.py`
- `backend/sim4/world/context.py`
- `backend/sim4/world/commands.py`
- `backend/sim4/runtime/command_bus.py`
- `backend/sim4/host/sim_runner.py`
- `backend/sim4/host/kvp_defaults.py`
- `backend/sim4/integration/live_session.py`
- `backend/sim4/integration/live_envelope.py`
- `backend/sim4/integration/export_overlays.py`
- `backend/sim4/integration/overlay_schemas.py`

Frontend:
- `frontend/loopforge-webview/src/app/boot.ts`
- `frontend/loopforge-webview/src/kvp/offline.ts`
- `frontend/loopforge-webview/src/kvp/client.ts`
- `frontend/loopforge-webview/src/state/worldStore.ts`
- `frontend/loopforge-webview/src/render/pixiScene.ts`
- `frontend/loopforge-webview/src/ui/hud.ts`
- `frontend/loopforge-webview/src/ui/devControls.ts`
- `frontend/loopforge-webview/src/styles/app.css`

