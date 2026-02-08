# Loopforge WebView + Sim4 Integration State

Last updated: 2026-02-08

This document is the current, end-to-end handoff for Loopforge's Sim4 -> KVP-0001 -> WebView pipeline. It summarizes what is wired, what is not, where the levers live, and the exact files/modules to touch. It also includes a full repo file tree at the end (excluding only `.git/`, `.venv/`, and `frontend/loopforge-webview/node_modules/` due to size and generated content).

---

## 1) End-to-End Data Path (What Actually Works Now)

**Working today, offline path:**

1. **World layout + sim** (backend) defines the factory campus with room bounds + floors.
   - `backend/sim4/world/loopforge_layout.py`
   - `backend/sim4/world/context.py`

2. **Sim runner** produces KVP-0001 snapshots/diffs.
   - `backend/sim4/host/sim_runner.py`
   - `backend/sim4/host/kvp_defaults.py`
   - `backend/sim4/integration/*`

3. **Offline demo artifacts** are generated into the webview’s public demo folder.
   - Generator: `scripts/run_sim4_kvp_demo.py`
   - Output: `frontend/loopforge-webview/public/demo/kvp_demo_1min`

4. **Webview (offline mode)** loads the manifest + ticks and renders the world using Pixi.
   - Loader: `frontend/loopforge-webview/src/kvp/offline.ts`
   - Boot: `frontend/loopforge-webview/src/app/boot.ts`
   - State: `frontend/loopforge-webview/src/state/worldStore.ts`
   - Renderer: `frontend/loopforge-webview/src/render/pixiScene.ts`

**Live WS path:**
- Client exists (`frontend/loopforge-webview/src/kvp/client.ts`) but only works if a live KVP websocket server is running. Not required for current visuals; not used by the offline demo pipeline.

---

## 2) Backend System State

### 2.1 World Layout + Room Data (Core to Viz)

**Canonical room layout is currently authored here:**
- `backend/sim4/world/loopforge_layout.py`

**Current layout details:**
- **Units:** meters, world bounds 500 x 500.
- **Tile size:** 20m (implicit in layout coordinates; viz uses 20 world units per tile).
- **Floors:**
  - Floor 0: main factory + residential + outdoor perimeter.
  - Floor 1: Supervisor Deck only.
- **Rooms:**
  - `Lobby Entry` (1x2, south edge) and `Elevator Core` (1x1, north of lobby).
  - `Brain Forge`, `Assembly Line`, `Resonance Hall`, `Cooling Vent Farms`, `Loading Yard`, `Habitation Block`, `Supervisor Deck`.

**Why this matters:**
- `RoomRecord.bounds` and `RoomRecord.level` are now emitted in KVP snapshots and are used by the webview to place rooms in the world. This is the critical alignment that restores the “factory layout” visuals.

### 2.2 World Context + Commands

- `backend/sim4/world/context.py`
  - Canonical room registry, agent registry, items registry.
  - Validates room existence when placing agents/items.

- `backend/sim4/world/commands.py`
  - Defines world commands (spawn/despawn items, door open/close, etc.).

### 2.3 ECS Runtime + Simulation

- `backend/sim4/ecs/*`
  - Components: `backend/sim4/ecs/components/embodiment.py` (Transform, RoomPresence), `backend/sim4/ecs/components/intent_action.py` (ActionState).
  - Systems are orchestrated by the scheduler you provide in the runner.

- `backend/sim4/runtime/*`
  - Tick clock and tick loop.

### 2.4 Snapshot + KVP Integration (SOP-100/SOP-200 compliant)

- Snapshot layer: `backend/sim4/snapshot/*`
  - Builds world snapshots and diffs per tick.

- KVP integration: `backend/sim4/integration/*`
  - `kvp_state_history.py`, `export_state.py`, `manifest_writer.py`, etc.
  - Responsible for KVP-0001 envelopes, manifest + diff file layout.

- Host defaults: `backend/sim4/host/kvp_defaults.py`
  - Default RenderSpec and RunAnchors for offline demo.

### 2.5 Offline Demo Generator (Current Source of Frontend Visuals)

- `scripts/run_sim4_kvp_demo.py`
  - Calls `apply_loopforge_layout` to seed rooms with bounds + floors.
  - Seeds agents inside room bounds (center + jitter).
  - Emits KVP artifacts to `frontend/loopforge-webview/public/demo/kvp_demo_1min`.

---

## 3) Frontend System State

### 3.1 Boot + Offline Playback

- `frontend/loopforge-webview/src/app/boot.ts`
  - Bootstraps Pixi scene and HUD.
  - Offline mode uses `startOfflineRun` to stream KVP diffs from local files.
  - `Dev Controls` are mounted here (floor switching + restart).

- `frontend/loopforge-webview/src/kvp/offline.ts`
  - Loads manifest + snapshots + diffs and applies them to the store.

- `frontend/loopforge-webview/src/kvp/client.ts`
  - WebSocket client for live KVP.

### 3.2 World Store (KVP Schema Surface)

- `frontend/loopforge-webview/src/state/worldStore.ts`
  - Defines KVP schema types used by renderer (`KvpRoom`, `KvpAgent`, `KvpItem`).
  - Adds `room.bounds`, `room.zone`, `room.level` support.

### 3.3 Rendering (Pixi WebView)

- `frontend/loopforge-webview/src/render/pixiScene.ts`
  - **Room placement:** If KVP provides `room.bounds`, those bounds are used (no fallback). If not, a tile-based layout is synthesized.
  - **Scale:** Uses `WORLD_UNITS_PER_TILE = 20` and converts world meters to iso coordinates.
  - **Room floors:** Uses `room.level` to drive floor filtering and elevation offset.
  - **Cutouts:** Animated wall cutouts via `roomCutout` and `tickRoomCutout` (smoothly interpolates wall opening/closing).
  - **Room selection:** clicking toggles cutout state.
  - **Items:** intentionally hidden for now (rendering commented/disabled).
  - **Agents:** rendered in-room with positions from `transform`.
  - **Paths:** neighbor links rendered; cross-floor links only show if a room label contains `elevator` or `lift`.

- `frontend/loopforge-webview/src/render/iso.ts`
  - Isometric projection helper; controlled via RenderSpec recommendations.

### 3.4 HUD + Dev Controls

- HUD panel: `frontend/loopforge-webview/src/ui/hud.ts`
  - Displays connection info, tick, step hash, etc.

- Dev controls: `frontend/loopforge-webview/src/ui/devControls.ts`
  - Floor switching: `All`, `F0`, `F1`.
  - Restart playback (offline only).

### 3.5 Styling

- `frontend/loopforge-webview/src/styles/app.css`
  - Pastel, graphic-novel tone to align with the art references.

---

## 4) What Is Wired End-to-End vs Not Yet Wired

**Wired and working now:**
- Room layout bounds and floors from backend -> KVP -> webview render.
- Offline playback with diffs + snapshots from local artifacts.
- Floor switching and restart playback via dev controls.
- Room selection and animated cutaway.

**Not wired (yet):**
- **Items rendering:** items exist in KVP data but are currently suppressed in renderer.
- **Agent path constraints:** agents are visually inside rooms, but movement constraints (doors, adjacency) are not enforced visually.
- **Live WS pipeline:** client exists, but depends on a live KVP server.
- **Interactive sim inputs:** UI controls do not send world commands to sim.

---

## 5) Development Levers (High-Impact Knobs)

### Backend
- **Room layout + bounds:** `backend/sim4/world/loopforge_layout.py`
  - Primary lever for spatial composition and floor structure.
- **RenderSpec:** `backend/sim4/host/kvp_defaults.py`
  - Controls world bounds, units, iso tile recommendation.
- **Offline artifact generation:** `scripts/run_sim4_kvp_demo.py`
  - Agents count, tick count, wander speed, item spawning.

### Frontend
- **World scale:** `frontend/loopforge-webview/src/render/pixiScene.ts`
  - `WORLD_UNITS_PER_TILE` is the current scale mapping to meters.
- **Cutout animation:** `pixiScene.ts` (`roomCutout`/`tickRoomCutout`).
- **Floor filtering:** `pixiScene.ts` (`setFloorFilter`).
- **Path rendering:** `pixiScene.ts` (neighbor logic; elevator gate).
- **Room materials and shading:** `pixiScene.ts` (palette + `roomColors`).
- **HUD + controls:** `frontend/loopforge-webview/src/ui/hud.ts`, `devControls.ts`.

---

## 6) Current Visual Output Summary

- The factory campus appears in isometric 2.5D with distinct room volumes.
- Floor 0 shows lobby, elevator, forge, assembly, resonance, cooling, loading, habitation.
- Floor 1 shows Supervisor Deck.
- Agents are centered inside room bounds and move subtly.
- Items are suppressed for clarity.

---

## 7) Full Repo File Tree

The tree below lists all files and directories as they exist in this working copy, **excluding**:
- `.git/`
- `.venv/`
- `legacy/`
- `frontend/loopforge-webview/node_modules/`
- `frontend/loopforge-webview/public/demo/`

These are generated/large and not part of core repo source.

```
.
./frontend
./frontend/loopforge-webview
./frontend/loopforge-webview/index.html
./frontend/loopforge-webview/.env.local
./frontend/loopforge-webview/public
./frontend/loopforge-webview/public/vite.svg
./frontend/loopforge-webview/.gitignore
./frontend/loopforge-webview/package-lock.json
./frontend/loopforge-webview/package.json
./frontend/loopforge-webview/tsconfig.json
./frontend/loopforge-webview/src
./frontend/loopforge-webview/src/ui
./frontend/loopforge-webview/src/ui/hud.ts
./frontend/loopforge-webview/src/ui/devControls.ts
./frontend/loopforge-webview/src/counter.ts
./frontend/loopforge-webview/src/app
./frontend/loopforge-webview/src/app/boot.ts
./frontend/loopforge-webview/src/main.ts
./frontend/loopforge-webview/src/env.d.ts
./frontend/loopforge-webview/src/render
./frontend/loopforge-webview/src/render/iso.ts
./frontend/loopforge-webview/src/render/pixiScene.ts
./frontend/loopforge-webview/src/state
./frontend/loopforge-webview/src/state/worldStore.ts
./frontend/loopforge-webview/src/styles
./frontend/loopforge-webview/src/styles/app.css
./frontend/loopforge-webview/src/typescript.svg
./frontend/loopforge-webview/src/kvp
./frontend/loopforge-webview/src/kvp/offline.ts
./frontend/loopforge-webview/src/kvp/client.ts
./frontend/loopforge-webview/src/debug
./frontend/loopforge-webview/src/debug/mockKernel.ts
./uv.lock
./.pytest_cache
./.pytest_cache/CACHEDIR.TAG
./.pytest_cache/README.md
./.pytest_cache/.gitignore
./.pytest_cache/v
./.pytest_cache/v/cache
./.pytest_cache/v/cache/nodeids
./.pytest_cache/v/cache/lastfailed
./.pytest_cache/v/cache/stepwise
./.pre-commit-config.yaml
./alembic.ini
./Dockerfile
./Makefile
./pyproject.toml
./backend
./backend/__init__.py
./backend/sim4
./backend/sim4/snapshot
./backend/sim4/snapshot/episode_types.py
./backend/sim4/snapshot/diff_types.py
./backend/sim4/snapshot/__init__.py
./backend/sim4/snapshot/world_snapshot.py
./backend/sim4/snapshot/__pycache__
./backend/sim4/snapshot/__pycache__/world_snapshot.cpython-311.pyc
./backend/sim4/snapshot/__pycache__/world_snapshot.cpython-312.pyc
./backend/sim4/snapshot/__pycache__/world_snapshot_builder.cpython-311.pyc
./backend/sim4/snapshot/__pycache__/diff_types.cpython-312.pyc
./backend/sim4/snapshot/__pycache__/snapshot_diff.cpython-312.pyc
./backend/sim4/snapshot/__pycache__/world_snapshot_builder.cpython-312.pyc
./backend/sim4/snapshot/__pycache__/diff_types.cpython-311.pyc
./backend/sim4/snapshot/__pycache__/snapshot_diff.cpython-311.pyc
./backend/sim4/snapshot/__pycache__/episode_builder.cpython-311.pyc
./backend/sim4/snapshot/__pycache__/episode_builder.cpython-312.pyc
./backend/sim4/snapshot/__pycache__/episode_types.cpython-311.pyc
./backend/sim4/snapshot/__pycache__/episode_types.cpython-312.pyc
./backend/sim4/snapshot/__pycache__/output.cpython-311.pyc
./backend/sim4/snapshot/__pycache__/__init__.cpython-312.pyc
./backend/sim4/snapshot/__pycache__/__init__.cpython-311.pyc
./backend/sim4/snapshot/episode_builder.py
./backend/sim4/snapshot/snapshot_diff.py
./backend/sim4/snapshot/output.py
./backend/sim4/snapshot/world_snapshot_builder.py
./backend/sim4/host
./backend/sim4/host/kvp_defaults.py
./backend/sim4/host/__init__.py
./backend/sim4/host/__pycache__
./backend/sim4/host/__pycache__/sim_runner.cpython-311.pyc
./backend/sim4/host/__pycache__/kvp_defaults.cpython-311.pyc
./backend/sim4/host/__pycache__/__init__.cpython-311.pyc
./backend/sim4/host/sim_runner.py
./backend/sim4/integration
./backend/sim4/integration/diff_ops.py
./backend/sim4/integration/schema_version.py
./backend/sim4/integration/kvp_envelope.py
./backend/sim4/integration/jcs.py
./backend/sim4/integration/live_session.py
./backend/sim4/integration/step_hash.py
./backend/sim4/integration/kvp_version.py
./backend/sim4/integration/overlay_schemas.py
./backend/sim4/integration/__init__.py
./backend/sim4/integration/__pycache__
./backend/sim4/integration/__pycache__/export_verify.cpython-311.pyc
./backend/sim4/integration/__pycache__/export_verify.cpython-312.pyc
./backend/sim4/integration/__pycache__/frame_builder.cpython-312.pyc
./backend/sim4/integration/__pycache__/manifest_writer.cpython-311.pyc
./backend/sim4/integration/__pycache__/jcs.cpython-312.pyc
./backend/sim4/integration/__pycache__/kvp_state_history.cpython-311.pyc
./backend/sim4/integration/__pycache__/manifest_writer.cpython-312.pyc
./backend/sim4/integration/__pycache__/jcs.cpython-311.pyc
./backend/sim4/integration/__pycache__/record_writer.cpython-311.pyc
./backend/sim4/integration/__pycache__/render_spec.cpython-312.pyc
./backend/sim4/integration/__pycache__/run_anchors.cpython-311.pyc
./backend/sim4/integration/__pycache__/live_envelope.cpython-311.pyc
./backend/sim4/integration/__pycache__/record_writer.cpython-312.pyc
./backend/sim4/integration/__pycache__/render_spec.cpython-311.pyc
./backend/sim4/integration/__pycache__/run_anchors.cpython-312.pyc
./backend/sim4/integration/__pycache__/kvp_version.cpython-312.pyc
./backend/sim4/integration/__pycache__/export_state.cpython-312.pyc
./backend/sim4/integration/__pycache__/kvp_envelope.cpython-311.pyc
./backend/sim4/integration/__pycache__/export_overlays.cpython-312.pyc
./backend/sim4/integration/__pycache__/ui_events.cpython-312.pyc
./backend/sim4/integration/__pycache__/live_sink.cpython-311.pyc
./backend/sim4/integration/__pycache__/kvp_version.cpython-311.pyc
./backend/sim4/integration/__pycache__/export_state.cpython-311.pyc
./backend/sim4/integration/__pycache__/kvp_envelope.cpython-312.pyc
./backend/sim4/integration/__pycache__/export_overlays.cpython-311.pyc
./backend/sim4/integration/__pycache__/render_specs.cpython-312.pyc
./backend/sim4/integration/__pycache__/overlay_schemas.cpython-311.pyc
./backend/sim4/integration/__pycache__/overlay_schemas.cpython-312.pyc
./backend/sim4/integration/__pycache__/types.cpython-312.pyc
./backend/sim4/integration/__pycache__/canonicalize.cpython-311.pyc
./backend/sim4/integration/__pycache__/schema_version.cpython-312.pyc
./backend/sim4/integration/__pycache__/canonicalize.cpython-312.pyc
./backend/sim4/integration/__pycache__/schema_version.cpython-311.pyc
./backend/sim4/integration/__pycache__/live_session.cpython-311.pyc
./backend/sim4/integration/__pycache__/diff_ops.cpython-311.pyc
./backend/sim4/integration/__pycache__/__init__.cpython-312.pyc
./backend/sim4/integration/__pycache__/step_hash.cpython-311.pyc
./backend/sim4/integration/__pycache__/manifest_schema.cpython-311.pyc
./backend/sim4/integration/__pycache__/__init__.cpython-311.pyc
./backend/sim4/integration/__pycache__/step_hash.cpython-312.pyc
./backend/sim4/integration/__pycache__/manifest_schema.cpython-312.pyc
./backend/sim4/integration/export_state.py
./backend/sim4/integration/record_writer.py
./backend/sim4/integration/canonicalize.py
./backend/sim4/integration/run_anchors.py
./backend/sim4/integration/live_sink.py
./backend/sim4/integration/export_verify.py
./backend/sim4/integration/manifest_writer.py
./backend/sim4/integration/live_envelope.py
./backend/sim4/integration/render_spec.py
./backend/sim4/integration/manifest_schema.py
./backend/sim4/integration/kvp_state_history.py
./backend/sim4/integration/export_overlays.py
./backend/sim4/runtime
./backend/sim4/runtime/events.py
./backend/sim4/runtime/clock.py
./backend/sim4/runtime/__init__.py
./backend/sim4/runtime/__pycache__
./backend/sim4/runtime/__pycache__/clock.cpython-312.pyc
./backend/sim4/runtime/__pycache__/clock.cpython-311.pyc
./backend/sim4/runtime/__pycache__/tick.cpython-312.pyc
./backend/sim4/runtime/__pycache__/tick.cpython-311.pyc
./backend/sim4/runtime/__pycache__/narrative_context.cpython-312.pyc
./backend/sim4/runtime/__pycache__/narrative_context.cpython-311.pyc
./backend/sim4/runtime/__pycache__/bubble_bridge.cpython-312.pyc
./backend/sim4/runtime/__pycache__/command_bus.cpython-312.pyc
./backend/sim4/runtime/__pycache__/events.cpython-312.pyc
./backend/sim4/runtime/__pycache__/command_bus.cpython-311.pyc
./backend/sim4/runtime/__pycache__/events.cpython-311.pyc
./backend/sim4/runtime/__pycache__/__init__.cpython-312.pyc
./backend/sim4/runtime/__pycache__/__init__.cpython-311.pyc
./backend/sim4/runtime/command_bus.py
./backend/sim4/runtime/narrative_context.py
./backend/sim4/runtime/tick.py
./backend/sim4/runtime/scheduler.py
./backend/sim4/tests
./backend/sim4/tests/snapshot
./backend/sim4/tests/snapshot/test_snapshot_diff.py
./backend/sim4/tests/snapshot/__pycache__
./backend/sim4/tests/snapshot/__pycache__/test_episode_builder.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/snapshot/__pycache__/test_snapshot_diff.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/snapshot/__pycache__/test_world_snapshot.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/snapshot/test_world_snapshot.py
./backend/sim4/tests/snapshot/test_episode_builder.py
./backend/sim4/tests/conftest.py
./backend/sim4/tests/integration
./backend/sim4/tests/integration/test_s14_5_export_layout_doc.py
./backend/sim4/tests/integration/test_s14_1_ssot.py
./backend/sim4/tests/integration/test_s14_2_canonicalization.py
./backend/sim4/tests/integration/__pycache__
./backend/sim4/tests/integration/__pycache__/test_s14_7_overlays.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/integration/__pycache__/test_s14_4_manifest.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/integration/__pycache__/test_s14_5_export_layout_doc.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/integration/__pycache__/test_s14_1_ssot.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/integration/__pycache__/test_s14_8_golden_fixture.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/integration/__pycache__/test_s14_3_envelope_records.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/integration/__pycache__/test_s14_2_canonicalization.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/integration/__pycache__/test_s14_6_export_state.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/integration/test_s14_7_overlays.py
./backend/sim4/tests/integration/test_s14_8_golden_fixture.py
./backend/sim4/tests/integration/test_s14_4_manifest.py
./backend/sim4/tests/integration/test_s14_3_envelope_records.py
./backend/sim4/tests/integration/test_s14_6_export_state.py
./backend/sim4/tests/runtime
./backend/sim4/tests/runtime/test_tick_skeleton.py
./backend/sim4/tests/runtime/test_tick_narrative_integration.py
./backend/sim4/tests/runtime/test_event_consolidation.py
./backend/sim4/tests/runtime/test_tick_system_execution.py
./backend/sim4/tests/runtime/test_command_bus_and_application.py
./backend/sim4/tests/runtime/__pycache__
./backend/sim4/tests/runtime/__pycache__/test_toy_simulation_tick.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/runtime/__pycache__/test_tick_phase_h_integration.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/runtime/__pycache__/test_tick_skeleton.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/runtime/__pycache__/test_clock.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/runtime/__pycache__/test_command_bus_and_application.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/runtime/__pycache__/test_event_consolidation.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/runtime/__pycache__/test_tick_system_execution.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/runtime/__pycache__/test_tick_narrative_integration.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/runtime/test_toy_simulation_tick.py
./backend/sim4/tests/runtime/test_tick_phase_h_integration.py
./backend/sim4/tests/runtime/test_clock.py
./backend/sim4/tests/narrative
./backend/sim4/tests/narrative/test_narrative_interface_dtos.py
./backend/sim4/tests/narrative/__pycache__
./backend/sim4/tests/narrative/__pycache__/test_narrative_runtime_context.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/narrative/__pycache__/test_narrative_interface_dtos.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/narrative/test_narrative_runtime_context.py
./backend/sim4/tests/world
./backend/sim4/tests/world/test_apply_world_commands.py
./backend/sim4/tests/world/test_world_commands_events.py
./backend/sim4/tests/world/__pycache__
./backend/sim4/tests/world/__pycache__/test_world_views.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/world/__pycache__/test_apply_world_commands.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/world/__pycache__/test_world_context.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/world/__pycache__/test_world_commands_events.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/world/test_world_context.py
./backend/sim4/tests/world/test_world_views.py
./backend/sim4/tests/ecs
./backend/sim4/tests/ecs/test_ecs_world_apply_commands_full.py
./backend/sim4/tests/ecs/test_ecs_world_apply_commands_basic.py
./backend/sim4/tests/ecs/test_ecs_substrate_sanity.py
./backend/sim4/tests/ecs/test_ecs_tick_simulation.py
./backend/sim4/tests/ecs/test_ecs_world_and_query.py
./backend/sim4/tests/ecs/test_ecs_command_buffer.py
./backend/sim4/tests/ecs/__pycache__
./backend/sim4/tests/ecs/__pycache__/test_query_signature.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/__pycache__/test_ecs_world_apply_commands_basic.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/__pycache__/test_ecs_commands.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/__pycache__/test_ecs_tick_simulation.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/__pycache__/test_ecs_archetype.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/__pycache__/test_ecs_storage.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/__pycache__/test_ecs_command_buffer.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/__pycache__/test_ecs_world_and_query.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/__pycache__/test_ecs_entity.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/__pycache__/test_ecs_substrate_sanity.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/__pycache__/test_ecs_world_apply_commands_full.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/components
./backend/sim4/tests/ecs/components/test_motive_plan_components.py
./backend/sim4/tests/ecs/components/test_drive_emotion_components.py
./backend/sim4/tests/ecs/components/test_identity_components.py
./backend/sim4/tests/ecs/components/test_belief_social_components.py
./backend/sim4/tests/ecs/components/__pycache__
./backend/sim4/tests/ecs/components/__pycache__/test_identity_components.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/components/__pycache__/test_embodiment_perception_components.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/components/__pycache__/test_belief_social_components.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/components/__pycache__/test_motive_plan_components.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/components/__pycache__/test_intent_inventory_meta_components.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/components/__pycache__/test_drive_emotion_components.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/components/test_embodiment_perception_components.py
./backend/sim4/tests/ecs/components/test_intent_inventory_meta_components.py
./backend/sim4/tests/ecs/test_ecs_storage.py
./backend/sim4/tests/ecs/test_query_signature.py
./backend/sim4/tests/ecs/test_ecs_commands.py
./backend/sim4/tests/ecs/test_ecs_archetype.py
./backend/sim4/tests/ecs/systems
./backend/sim4/tests/ecs/systems/test_scheduler_order.py
./backend/sim4/tests/ecs/systems/test_phase_bc_systems_skeleton.py
./backend/sim4/tests/ecs/systems/__pycache__
./backend/sim4/tests/ecs/systems/__pycache__/test_systems_integration_skeleton.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/systems/__pycache__/test_systems_base.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/systems/__pycache__/test_phase_bc_systems_skeleton.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/systems/__pycache__/test_phase_de_systems_skeleton.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/systems/__pycache__/test_scheduler_order.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/ecs/systems/test_systems_integration_skeleton.py
./backend/sim4/tests/ecs/systems/test_systems_base.py
./backend/sim4/tests/ecs/systems/test_phase_de_systems_skeleton.py
./backend/sim4/tests/ecs/test_ecs_entity.py
./backend/sim4/tests/__pycache__
./backend/sim4/tests/__pycache__/test_ecs_world_apply_commands_basic.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/__pycache__/conftest.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/__pycache__/test_ecs_commands.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/__pycache__/test_ecs_tick_simulation.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/__pycache__/test_ecs_archetype.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/__pycache__/test_ecs_storage.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/__pycache__/test_ecs_command_buffer.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/__pycache__/test_ecs_world_and_query.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/__pycache__/test_ecs_entity.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/__pycache__/test_ecs_substrate_sanity.cpython-312-pytest-9.0.1.pyc
./backend/sim4/tests/__pycache__/test_ecs_world_apply_commands_full.cpython-312-pytest-9.0.1.pyc
./backend/sim4/narrative
./backend/sim4/narrative/interface.py
./backend/sim4/narrative/__init__.py
./backend/sim4/narrative/__pycache__
./backend/sim4/narrative/__pycache__/interface.cpython-312.pyc
./backend/sim4/narrative/__pycache__/__init__.cpython-312.pyc
./backend/sim4/__init__.py
./backend/sim4/world
./backend/sim4/world/loopforge_layout.py
./backend/sim4/world/events.py
./backend/sim4/world/__init__.py
./backend/sim4/world/__pycache__
./backend/sim4/world/__pycache__/loopforge_layout.cpython-311.pyc
./backend/sim4/world/__pycache__/views.cpython-312.pyc
./backend/sim4/world/__pycache__/views.cpython-311.pyc
./backend/sim4/world/__pycache__/context.cpython-312.pyc
./backend/sim4/world/__pycache__/context.cpython-311.pyc
./backend/sim4/world/__pycache__/apply_world_commands.cpython-311.pyc
./backend/sim4/world/__pycache__/apply_world_commands.cpython-312.pyc
./backend/sim4/world/__pycache__/commands.cpython-312.pyc
./backend/sim4/world/__pycache__/commands.cpython-311.pyc
./backend/sim4/world/__pycache__/events.cpython-312.pyc
./backend/sim4/world/__pycache__/events.cpython-311.pyc
./backend/sim4/world/__pycache__/__init__.cpython-312.pyc
./backend/sim4/world/__pycache__/__init__.cpython-311.pyc
./backend/sim4/world/apply_world_commands.py
./backend/sim4/world/context.py
./backend/sim4/world/commands.py
./backend/sim4/world/views.py
./backend/sim4/ecs
./backend/sim4/ecs/world.py
./backend/sim4/ecs/query.py
./backend/sim4/ecs/__init__.py
./backend/sim4/ecs/__pycache__
./backend/sim4/ecs/__pycache__/storage.cpython-312.pyc
./backend/sim4/ecs/__pycache__/storage.cpython-311.pyc
./backend/sim4/ecs/__pycache__/world.cpython-312.pyc
./backend/sim4/ecs/__pycache__/entity.cpython-311.pyc
./backend/sim4/ecs/__pycache__/world.cpython-311.pyc
./backend/sim4/ecs/__pycache__/entity.cpython-312.pyc
./backend/sim4/ecs/__pycache__/commands.cpython-312.pyc
./backend/sim4/ecs/__pycache__/archetype.cpython-311.pyc
./backend/sim4/ecs/__pycache__/commands.cpython-311.pyc
./backend/sim4/ecs/__pycache__/archetype.cpython-312.pyc
./backend/sim4/ecs/__pycache__/query.cpython-311.pyc
./backend/sim4/ecs/__pycache__/__init__.cpython-312.pyc
./backend/sim4/ecs/__pycache__/query.cpython-312.pyc
./backend/sim4/ecs/__pycache__/__init__.cpython-311.pyc
./backend/sim4/ecs/components
./backend/sim4/ecs/components/social.py
./backend/sim4/ecs/components/motive_plan.py
./backend/sim4/ecs/components/__init__.py
./backend/sim4/ecs/components/embodiment.py
./backend/sim4/ecs/components/__pycache__
./backend/sim4/ecs/components/__pycache__/drives.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/drives.cpython-312.pyc
./backend/sim4/ecs/components/__pycache__/motive_plan.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/motive_plan.cpython-312.pyc
./backend/sim4/ecs/components/__pycache__/social.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/narrative_state.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/emotion.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/social.cpython-312.pyc
./backend/sim4/ecs/components/__pycache__/narrative_state.cpython-312.pyc
./backend/sim4/ecs/components/__pycache__/emotion.cpython-312.pyc
./backend/sim4/ecs/components/__pycache__/inventory.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/meta.cpython-312.pyc
./backend/sim4/ecs/components/__pycache__/embodiment.cpython-312.pyc
./backend/sim4/ecs/components/__pycache__/inventory.cpython-312.pyc
./backend/sim4/ecs/components/__pycache__/meta.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/embodiment.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/perception.cpython-312.pyc
./backend/sim4/ecs/components/__pycache__/__init__.cpython-312.pyc
./backend/sim4/ecs/components/__pycache__/intent_action.cpython-312.pyc
./backend/sim4/ecs/components/__pycache__/belief.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/identity.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/perception.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/__init__.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/intent_action.cpython-311.pyc
./backend/sim4/ecs/components/__pycache__/belief.cpython-312.pyc
./backend/sim4/ecs/components/__pycache__/identity.cpython-312.pyc
./backend/sim4/ecs/components/belief.py
./backend/sim4/ecs/components/intent_action.py
./backend/sim4/ecs/components/narrative_state.py
./backend/sim4/ecs/components/emotion.py
./backend/sim4/ecs/components/perception.py
./backend/sim4/ecs/components/identity.py
./backend/sim4/ecs/components/drives.py
./backend/sim4/ecs/components/meta.py
./backend/sim4/ecs/components/inventory.py
./backend/sim4/ecs/storage.py
./backend/sim4/ecs/archetype.py
./backend/sim4/ecs/entity.py
./backend/sim4/ecs/systems
./backend/sim4/ecs/systems/drive_update_system.py
./backend/sim4/ecs/systems/interaction_resolution_system.py
./backend/sim4/ecs/systems/emotion_gradient_system.py
./backend/sim4/ecs/systems/movement_resolution_system.py
./backend/sim4/ecs/systems/social_update_system.py
./backend/sim4/ecs/systems/perception_system.py
./backend/sim4/ecs/systems/__init__.py
./backend/sim4/ecs/systems/__pycache__
./backend/sim4/ecs/systems/__pycache__/interaction_resolution_system.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/plan_resolution_system.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/movement_resolution_system.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/base.cpython-311.pyc
./backend/sim4/ecs/systems/__pycache__/base.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/intent_resolver_system.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/action_execution_system.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/inventory_system.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/scheduler_order.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/perception_system.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/cognitive_preprocessor.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/motive_formation_system.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/drive_update_system.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/social_update_system.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/__init__.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/emotion_gradient_system.cpython-312.pyc
./backend/sim4/ecs/systems/__pycache__/__init__.cpython-311.pyc
./backend/sim4/ecs/systems/intent_resolver_system.py
./backend/sim4/ecs/systems/scheduler_order.py
./backend/sim4/ecs/systems/motive_formation_system.py
./backend/sim4/ecs/systems/action_execution_system.py
./backend/sim4/ecs/systems/plan_resolution_system.py
./backend/sim4/ecs/systems/cognitive_preprocessor.py
./backend/sim4/ecs/systems/base.py
./backend/sim4/ecs/systems/inventory_system.py
./backend/sim4/ecs/commands.py
./backend/sim4/__pycache__
./backend/sim4/__pycache__/__init__.cpython-312.pyc
./backend/sim4/__pycache__/__init__.cpython-311.pyc
./backend/__pycache__
./backend/__pycache__/__init__.cpython-312.pyc
./backend/__pycache__/__init__.cpython-311.pyc
./docs
./docs/handovers
./docs/handovers/WEBVIEW_SYSTEM_STATE.md
./docs/handovers/WEBVIEW_VISUAL_HANDOFF.md
./docs/legacy
./docs/legacy/sprints
./docs/legacy/sprints/Helios
./docs/legacy/sprints/Helios/HELIOS_INITIAL_SPEC_ERA_II.md
./docs/legacy/sprints/Helios/HELIOS_PHASE_3_CLOSURE_REPORT.md
./docs/legacy/sprints/Helios/HELIOS_PHASE_2_CLOSURE_REPORT.md
./docs/legacy/sprints/Marquee
./docs/legacy/sprints/Marquee/MARQUEE_SPRINT_2_CLOSURE_REPORT.md
./docs/legacy/sprints/Marquee/MARQUEE_SPRINT_3_CLOSURE_REPORT.md
./docs/legacy/sprints/Marquee/MARQUEE_SPRINT_5_CLOSURE_REPORT.md
./docs/legacy/sprints/Marquee/MARQUEE_SPRINT_4_CLOSURE_REPORT.md
./docs/legacy/sprints/Marquee/MARQUEE_SPRINT_1_CLOSURE_REPORT.md
./docs/legacy/sprints/Marquee/MARQUEE_SPRINT_3_RESPEC.md
./docs/legacy/sprints/Stagemaker
./docs/legacy/sprints/Stagemaker/episode_identity_investigation.md
./docs/legacy/sprints/Stagemaker/phase_0_stage_api_foundations
./docs/legacy/sprints/Stagemaker/phase_0_stage_api_foundations/STAGEMAKER_PHASE_1_SPEC.md
./docs/legacy/sprints/Stagemaker/episode_identity_sprint2_report.md
./docs/legacy/sprints/Stagemaker/episode_identity_sprint1_report.md
./docs/legacy/sprints/Stagemaker/episode_identity_foundations.md
./docs/legacy/sprints/Gantry
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_8_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_E_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_8_RESPEC.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_D_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_B_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_2_RESPEC.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_G_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_INITIAL_SPEC_LOOPFORGE_LAYERING.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_F_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_7_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_2_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_6_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_3_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_5_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_H_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_4_CLOSURE_REPORT.md
./docs/legacy/sprints/Gantry/GANTRY_SPRINT_1_CLOSURE_REPORT.md
./docs/legacy/sim2
./docs/legacy/sim2/narrative
./docs/legacy/sim2/narrative/CHARACTER_BIBLE.md
./docs/legacy/sim2/narrative/EMOTIONAL_ARC_ENGINE.md
./docs/legacy/sim2/narrative/PRODUCER_VISION.md
./docs/legacy/sim2/narrative/CINEMATIC_DEBUGGER.md
./docs/legacy/sim2/sim3
./docs/legacy/sim2/sim3/ERA_III_IDENTITY_TYPES.md
./docs/legacy/sim2/sim3/ERA_III_IDENTITY_IMPLEMENTATION.md
./docs/legacy/sim2/qa
./docs/legacy/sim2/qa/SIM3_QA_TESTING_STRATEGY.md
./docs/legacy/sim2/loopforge-meta
./docs/legacy/sim2/loopforge-meta/HUMAN_AGENT_INTERACTION.md
./docs/legacy/sim2/loopforge-meta/LOOPFORGE_WHITEPAPER_DRAFT.md
./docs/legacy/sim2/loopforge-meta/HOW_IS_LOOPFORGE_DEVELOPED.md
./docs/legacy/sim2/loopforge-meta/prompts
./docs/legacy/sim2/loopforge-meta/prompts/LOOPFORGE_OUTPUT_SCHEMAS.md
./docs/legacy/sim2/loopforge-meta/prompts/JUNIE_SYSTEM_PROMPT.md
./docs/legacy/sim2/loopforge-meta/prompts/JUNIE_SIM3_BACKEND_SYSTEM_PROMPT.md
./docs/legacy/sim2/loopforge-meta/prompts/JUNIE_FULLSTACK_SYSTEM_PROMPT.md
./docs/legacy/sim2/loopforge-meta/prompts/JUNIE_PLAYBOOK.md
./docs/legacy/sim2/loopforge-meta/prompts/LLM_ARCHITECT_FIELD_MANUAL.md
./docs/legacy/sim2/loopforge-meta/MULTI_AGENT_WORKFLOW_GUIDELINES.md
./docs/legacy/sim2/loopforge-meta/meta-agents
./docs/legacy/sim2/loopforge-meta/meta-agents/snapshotter
./docs/legacy/sim2/loopforge-meta/meta-agents/snapshotter/DEBUGGING_CARTOGRAPHER.md
./docs/legacy/sim2/loopforge-meta/meta-agents/snapshotter/SNAPSHOTTER_TRIGGER_PROMPT.md
./docs/legacy/sim2/loopforge-meta/meta-agents/snapshotter/SNAPSHOTTER_SYSTEM_PROMPT.md
./docs/legacy/sim2/loopforge-meta/meta-agents/snapshotter/SNAPSHOTTER_AGENT_SPECIFICATION.md
./docs/legacy/sim2/loopforge-meta/meta-agents/architect
./docs/legacy/sim2/loopforge-meta/meta-agents/architect/AGENT_PROFILE_LLM_ARCHITECT.md
./docs/legacy/sim2/loopforge-meta/meta-agents/drift_analyst
./docs/legacy/sim2/loopforge-meta/meta-agents/orchestrator
./docs/legacy/sim2/loopforge-meta/meta-agents/orchestrator/ORCHESTRATOR_AGENT_SPECIFICATION.md
./docs/legacy/sim2/psych
./docs/legacy/sim2/psych/DIAGNOSTIC_PHILOSOPHY.md
./docs/legacy/sim2/psych/THE_PUPPETTEER_DOCTRINE.md
./docs/legacy/sim2/psych/memory
./docs/legacy/sim2/psych/memory/LOOPFORGE_MEMORY_SPEC.md
./docs/legacy/sim2/psych/memory/LOOPFORGE_MODEL_CONTEXT_MEMORY.md
./docs/legacy/sim2/psych/memory/LOOPFORGE_MEMORY_PRE_SPEC.md
./docs/legacy/sim2/psych/THE_PUPPETTEER_README.md
./docs/legacy/sim2/psych/COGNITIVE_ARCHITECTURE_SPEC.md
./docs/legacy/sim2/psych/SUPERVISOR_ACTIVITY.md
./docs/legacy/sim2/psych/LOOPFORGE_AGENT_VISION.md
./docs/legacy/sim2/psych/beliefs
./docs/legacy/sim2/psych/attribution
./docs/legacy/sim2/psych/attribution/ATTRIBUTION_QUICKSTART.md
./docs/legacy/sim2/psych/attribution/BELIEF_ATTRIBUTION.md
./docs/legacy/sim2/architecture
./docs/legacy/sim2/architecture/architect_chat_history
./docs/legacy/sim2/architecture/architect_chat_history/architects_producer_full_history.md
./docs/legacy/sim2/architecture/architect_chat_history/architects_hinge_full_history.md
./docs/legacy/sim2/architecture/architect_chat_history/architects_lumen_full_history.md
./docs/legacy/sim2/architecture/AAA_ROBOT_ASYLUM.md
./docs/legacy/sim2/architecture/layers
./docs/legacy/sim2/architecture/layers/LOOPFORGE_LAYERING_MODEL_WITH_VIZ.md
./docs/legacy/sim2/architecture/layers/LOOPFORGE_LAYERING_MODEL.md
./docs/legacy/sim2/architecture/identity
./docs/legacy/sim2/architecture/identity/LOOPFORGE_IDENTITY_STABILITY.md
./docs/legacy/sim2/architecture/identity/LOOPFORGE_IDENTITY_MODEL_V2.md
./docs/legacy/sim2/architecture/identity/LOOPFORGE_IDENTITY_MODEL.md
./docs/legacy/sim2/architecture/ENGINE_ARCHITECTURE.md
./docs/legacy/sim2/architecture/architecture_snapshots
./docs/legacy/sim2/architecture/architecture_snapshots/ARCH_SUMMARY_SNAPSHOT_2025-11-19_BEFORE_MOVING_BOXES.json
./docs/legacy/sim2/architecture/architecture_snapshots/ARCH_SUMMARY_SNAPSHOT_2025-11-21_AFTER_MOVING_BOXES.json
./docs/legacy/sim2/architecture/evolution
./docs/legacy/sim2/architecture/evolution/SIM3_BACKEND_BUILD_ORDER.md
./docs/legacy/sim2/architecture/evolution/LOOPFORGE_ARCHITECTURE_MIGRATION_REPORT_1.md
./docs/legacy/sim2/architecture/evolution/BACKEND_FRONTEND_ARCHITECHTURE_ALIGNMENT.md
./docs/legacy/sim2/architecture/evolution/NOTES_FROM_PREVIOUS_ARCHITECTS.md
./docs/legacy/sim2/architecture/evolution/ERA_III_BACKEND_VISION.md
./docs/legacy/sim2/architecture/evolution/EXPECTATION_FROM_BACKEND_1.md
./docs/legacy/sim2/architecture/evolution/ARCHITECTURE_EVOLUTION_PLAN.md
./docs/legacy/sim2/dev
./docs/legacy/sim2/dev/IMPLEMENTATION_STAGE_MAP_PHASE4A.md
./docs/legacy/sim2/dev/implementation_report_era_ii_mood_banner_and_test_fixes.md
./docs/legacy/sim2/dev/dev_reporting.md
./docs/legacy/sim2/dev/IMPLEMENTATION_REPORT_ARC_MOOD_V2_AND_BANNER.md
./docs/legacy/sim2/dev/IMPLEMENTATION_REPORT_DAY_STORYBOARD_PHASE2.md
./docs/legacy/sim2/dev/test_report_AppRouter_failures.md
./docs/legacy/sim2/dev/dev_stage_frontend.md
./docs/legacy/sim2/dev/implementation_report_era_ii_narrativeblockv2.md
./docs/legacy/sim2/dev/IMPLEMENTATION_AGENT_IDENTITY_PHASE3_SUMMARY.md
./docs/legacy/sim2/dev/debugging
./docs/legacy/sim2/dev/debugging/DEBUGGING_FRONTEND_ROUTER.md
./docs/legacy/sim2/dev/debugging/DEBUGGING_FRONTEND.md
./docs/legacy/sim2/dev/debugging/DEBUGGING_LOADING_SCREEN.md
./docs/legacy/sim2/dev/IMPLEMENTATION_REPORT_PHASE_2C_SCROLL_SYNC.md
./docs/legacy/sim2/dev/IMPLEMENTATION_STAGE_VIEW_PHASE4D.md
./docs/legacy/sim2/dev/test_report_ui-stage_current_failures.md
./docs/legacy/sim2/dev/note_episode_arc_mood_vs_day_detail.md
./docs/legacy/sim2/dev/IMPLEMENTATION_AGENT_IDENTITY_3A.md
./docs/legacy/sim2/dev/implementation_report_era_ii_spine_and_identity.md
./docs/legacy/sim2/dev/IMPLEMENTATION_REPORT_DAY_STORYBOARD_SPRINT_2A.md
./docs/legacy/sim2/dev/test_failure_report_EpisodeMoodBannerV1.md
./docs/legacy/sim2/dev/test_report_ui-stage_vitest.md
./docs/legacy/sim2/dev/IMPLEMENTATION_STAGE_MAP_PHASE4B.md
./docs/legacy/sim2/dev/reports
./docs/legacy/sim2/dev/reports/FRONT_END_SPRINT_1_4_FOLLOW_UP.md
./docs/legacy/sim2/dev/reports/2025-11-24_sprint4_1_story_vm_and_tension_visuals_report.md
./docs/legacy/sim2/dev/reports/2025-11-24_test_investigation.md
./docs/legacy/visual
./docs/legacy/visual/STAGE_VISION.md
./docs/legacy/visual/ERA_II_VISION.md
./docs/legacy/visual/ERA_II_HANDOFF.md
./docs/legacy/visual/FRONTEND_ARCHITECTURE_OVERVIEW.md
./docs/legacy/visual/LOOPFORGE_STAGE_ROADMAP.md
./docs/legacy/visual/ERA_I_HANDOFF.md
./docs/sim4
./docs/sim4/.DS_Store
./docs/sim4/sprints
./docs/sim4/sprints/SIM4_SPRINT_14.0.md
./docs/sim4/sprints/SIM4_SPRINT_8_SUBSPRINT_PLAN.md
./docs/sim4/sprints/SIM4_SPRINT_14_RESPEC2.md
./docs/sim4/sprints/SIM4_SPRINT_1_CLOSURE_REPORT_ECS_CORE_1.md
./docs/sim4/sprints/SIM4_SPRINTS_9_14_PLAN.md
./docs/sim4/sprints/SIM4_SPRINT_4_CLOSURE_REPORT_ECS_SYSTEMS.md
./docs/sim4/sprints/SIM4_SPRINT_7.4_RESPEC.md
./docs/sim4/sprints/SIM4_SPRINT_2_CLOSURE_REPORT_ECS_CORE_2.md
./docs/sim4/sprints/SIM4_SPRINT_6_CLOSURE_REPORT_RUNTIME_TICK_PIPELINE.md
./docs/sim4/sprints/SIM4_SPRINTS_1_8_CLOSURE_REPORT.md
./docs/sim4/sprints/SIM4_SPRINT_5_CLOSURE_REPORT_WORLD_ENGINE_CORE.md
./docs/sim4/sprints/SIM4_SPRINT_7_SUBSPRINT_PLAN.md
./docs/sim4/sprints/SIM4_SPRINT_14_RESPEC.md
./docs/sim4/SOTs
./docs/sim4/SOTs/SOT-SIM4-NARRATIVE-INTERFACE.md
./docs/sim4/SOTs/SOT-SIM4-RUNTIME-TICK.md
./docs/sim4/SOTs/SOT-SIM4-WORLD-ENGINE.md
./docs/sim4/SOTs/SOT-SIM4-ECS-SYSTEMS.md
./docs/sim4/SOTs/SOT-SIM4-ECS-SUBSTRATE-COMPONENTS-DETAILS.md
./docs/sim4/SOTs/SOT-SIM4-RUNTIME-WORLDCONTEXT.md
./docs/sim4/SOTs/SOT-SIM4-ECS-CORE.md
./docs/sim4/SOTs/SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT.md
./docs/sim4/SOTs/SOT-SIM4-SNAPSHOT-AND-EPISODE.md
./docs/sim4/SOTs/SOT-SIM4-ENGINE v1.0.md
./docs/sim4/SOTs/SOT-SIM4-ECS-SUBSTRATE-COMPONENTS.md
./docs/sim4/SOTs/SOT-SIM4-ECS-COMMANDS-AND-EVENTS.md
./docs/sim4/prompts
./docs/sim4/prompts/JUNIE_SIM4_SYSTEM_PROMPT.md
./docs/sim4/prompts/JUNIE_SIM4_SPRINTS_9_14_SYSTEM_PROMPT.md
./docs/sim4/prompts/JUNIE_SIM4_SYSTEM_PROMPT_SPRINTS_5_8.md
./docs/sim4/dev
./docs/sim4/dev/reports
./docs/sim4/dev/reports/2025-12-01_sim4_ecs_inconsistency_audit.md
./docs/sim4/dev/reports/2025-12-01_sim4_ecs_implementation_overview.md
./docs/sim4/dev/reports/2025-12-01_world_engine_implementation_report.md
./docs/sim4/SOPs
./docs/sim4/SOPs/FREE_AGENT_SPEC.md
./docs/sim4/SOPs/SOP-100 — Layer Boundary Protection.md
./docs/sim4/SOPs/SOP-300 — ECS Component & System Lifecycle Contract.md
./docs/sim4/SOPs/SOP-000 — Architect Operating Contract (AOC).md
./docs/sim4/SOPs/SIMX_VISION.md
./docs/sim4/SOPs/SOP-500 — Deterministic layout.md
./docs/sim4/SOPs/SOP-400 — Final Blessing.md
./docs/sim4/SOPs/SOP-200 — Determinism & Simulation Contract.md
./docs/sim4/reports
./docs/sim4/reports/SIM4_FOLDER_TREE.md
./docs/sim4/reports/IMPLEMENTATION_VS_SOT_RUNTIME_NARRATIVE_CONTEXT.md
./docs/sim5
./docs/sim5/SOPs
./docs/sim5/SOPs/KVP-0001 v0.1 Compliance Checklist.md
./docs/sim5/SOPs/KVP-0001 — Million-dollar plan v1.0.md
./docs/sim5/SOPs/WEBVIEW-0003.md
./docs/sim5/SOPs/KVP-0001.md
./docs/sim5/SOPs/SIM5_LLM_ARCHITECT_SYSTEM_PROMPT.md
./docs/sim5/SOPs/WEBVIEW-0002.md
./docs/sim5/SOPs/WEBVIEW-0001.md
./docs/sim5/SOPs/KVP-0001 — Semantics v0.1.md
./docs/sim5/SOPs/SIM5_VISION.md
./docs/sim5/SOPs/VIEW-0001.md
./docs/sim5/SOPs/KVP-0001 — Canonicalization & Hashing.md
./docs/kvp_export_layout_v0_1.md
./docs/sprint14_scope_lock.md
./docs/templates
./docs/templates/exporter_header_S14.txt
./docs/templates/s14_non_goals_checklist.md
./docs/export
./docs/export/run_layout.md
./docs/reports
./docs/reports/sprint_14_1B_preflight.md
./scratch.py
./README.md
./.gitignore
./CONTRIBUTING.md
./scripts
./scripts/run_sim4_kvp_demo.py
./scripts/generate_small_run_fixture.py
./loopforge_city.egg-info
./loopforge_city.egg-info/PKG-INFO
./loopforge_city.egg-info/SOURCES.txt
./loopforge_city.egg-info/requires.txt
./loopforge_city.egg-info/top_level.txt
./loopforge_city.egg-info/dependency_links.txt
./fixtures
./fixtures/kvp
./fixtures/kvp/v0_1
./fixtures/kvp/v0_1/small_run
./fixtures/kvp/v0_1/small_run/overlays
./fixtures/kvp/v0_1/small_run/overlays/psycho_frames.jsonl
./fixtures/kvp/v0_1/small_run/overlays/ui_events.jsonl
./fixtures/kvp/v0_1/small_run/state
./fixtures/kvp/v0_1/small_run/state/snapshots
./fixtures/kvp/v0_1/small_run/state/snapshots/tick_0000000000.kvp.json
./fixtures/kvp/v0_1/small_run/state/snapshots/tick_0000000002.kvp.json
./fixtures/kvp/v0_1/small_run/state/diffs
./fixtures/kvp/v0_1/small_run/state/diffs/from_0000000000_to_0000000001.kvp.json
./fixtures/kvp/v0_1/small_run/state/diffs/from_0000000002_to_0000000003.kvp.json
./fixtures/kvp/v0_1/small_run/state/diffs/from_0000000001_to_0000000002.kvp.json
./fixtures/kvp/v0_1/small_run/fixture_hashes.json
./fixtures/kvp/v0_1/small_run/manifest.kvp.json
./docker-compose.yml
./alembic
./alembic/script.py.mako
./alembic/env.py
./alembic/versions
./alembic/versions/__pycache__
./alembic/versions/__pycache__/0001_initial.cpython-312.pyc
./alembic/versions/__pycache__/0002_traits_and_defaults.cpython-312.pyc
./alembic/versions/0001_initial.py
./alembic/versions/0002_traits_and_defaults.py
./alembic/__pycache__
./alembic/__pycache__/env.cpython-312.pyc
./.gitmessage
./loopforge_test.db
./.cz.toml
./main.py
./runs
./runs/kvp_demo_1min
./runs/kvp_demo_1min/state
./runs/kvp_demo_1min/state/snapshots
./runs/kvp_demo_1min/state/diffs
```
