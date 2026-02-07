# Loopforge Webview Visual Handoff (Next Chat)

You are continuing work in the repo at `frontend/loopforge-webview`. The viewer is now wired to KVP-0001 offline artifacts and renders, but visuals are still early and “diagram-like.” The goal is to evolve it into a real-world feeling visualization: stable world layout, believable spatial structure, and agents moving through space with intent (not drifting).

## Current State (What’s Done)
- Offline artifacts are consumed directly from a KVP export folder.
- Default viewer mode is offline and loads `/demo/kvp_demo_1min`.
- KVP `FULL_SNAPSHOT` + `FRAME_DIFF(ops[])` pipeline is implemented; state is applied via ops, not state replacement.
- Pixi renderer is a noir-neon “tech blueprint” starting point, but the scene still reads as abstract.

## Runtime Architecture Overview
- Offline flow: `manifest.kvp.json` → load keyframe snapshot → apply per-tick diff ops → render.
- Live flow: WS client does KVP handshake, `FULL_SNAPSHOT`, then `FRAME_DIFF` ops.
- The viewer is protocol-first and deterministic: it never mutates sim state, only applies KVP messages.

### Core Frontend Components (Code References)
- **State store**: `frontend/loopforge-webview/src/state/worldStore.ts`
  - Holds `rooms`, `agents`, `items`, `events` as Maps.
  - `applySnapshot()` and `applyDiff()` handle ops.
- **Offline loader**: `frontend/loopforge-webview/src/kvp/offline.ts`
  - Loads `manifest.kvp.json`, fetches records, applies diffs in order.
  - Supports playback speed via env (`VITE_WEBVIEW_SPEED`).
- **KVP live client**: `frontend/loopforge-webview/src/kvp/client.ts`
  - WebSocket handshake, subscribe, snapshot/diff dispatch.
- **Renderer**: `frontend/loopforge-webview/src/render/pixiScene.ts`
  - Stable room layout + auto-fit camera.
  - Renders grid, rooms, items, agents.
- **Iso projection**: `frontend/loopforge-webview/src/render/iso.ts`
  - Mutable tile size from render_spec.
- **Boot**: `frontend/loopforge-webview/src/app/boot.ts`
  - Offline by default; uses env vars.
- **Styles**: `frontend/loopforge-webview/src/styles/app.css`
- **HUD**: `frontend/loopforge-webview/src/ui/hud.ts`

## Demo Run
- Offline artifacts live at `frontend/loopforge-webview/public/demo/kvp_demo_1min`.
- Default base URL is `/demo/kvp_demo_1min`.

## Goal For This Chat
Make the world feel “real”: stable terrain, readable zones, depth, spatial coherence. Agents should move through believable space rather than floating in place.

## Recommended Next Steps (Visual Goals)
1. **World layout & geometry**
   - Derive room geometry from world bounds and room adjacency instead of centroid scatter.
   - Consider grid-based “city block” or iso-tile floor with room shapes occupying actual tiles.
   - Use `render_spec` bounds and projection hints.

2. **Agent visuals & motion**
   - Add interpolation (lerp) between ticks to smooth motion.
   - Render agents as sprites or stylized silhouettes, not only rings.
   - Optional: directional facing based on velocity vector.

3. **World dressing**
   - Add ambient floor texture, light pools, glow zones, faint parallax.
   - Represent items as static props or glowing markers in rooms.

4. **Camera & framing**
   - Add a “Recenter” control or a follow toggle.
   - Optional: zoom based on room density.

## Must-Read Docs (In Order)
1. `docs/sim5/SOPs/KVP-0001.md`
   - Core protocol contract.
2. `docs/sim5/SOPs/KVP-0001 — Semantics v0.1.md`
   - Diff/ops semantics: `FRAME_DIFF` must contain `ops[]`, no `payload.state`.
3. `docs/sim5/SOPs/WEBVIEW-0001.md`
   - Pixi viewer reference & boot architecture.
4. `docs/sim5/SOPs/WEBVIEW-0003.md`
   - Offline viewer contract (manifest/diff replay).
5. `docs/export/run_layout.md`
   - Exact export folder layout.

## Data Shape Notes (Critical)
- Snapshot payload format:
  - `payload.state.rooms`, `payload.state.agents`, `payload.state.items`, `payload.state.events`
- Agents have `transform: { x, y, room_id }` with continuous coords.
- Rooms currently have no `bounds` in KVP; layout must be derived.
- Diff ops are `UPSERT_* / REMOVE_*` for rooms, agents, items, events.

## Quality Bar
- Viewer stays protocol-pure (no sim logic).
- Visuals read as a coherent world, not abstract nodes.
- Movement feels intentional and spatially grounded.
- Scene is legible and expressive even without narration.
