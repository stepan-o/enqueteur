# SIM4 SPRINTS 9-14 PLAN: “Viewer Readiness”

Goal: by the end, we can **export a run**, **load it in a Godot-like viewer**, **scrub time (rewind/zoom)**, render **2.5D/isometric placeholders**, show **bubbles**, and overlay **psycho topology** — without violating SOP-100/200.

---

## Sprint 9 — Integration Spine (Run Export + Schemas)

### S9.1 — Create `integration/` package + versioned schemas
**Deliverables**
- `backend/sim4/integration/__init__.py`
- `integration/schema_version.py` (single source of truth: `INTEGRATION_SCHEMA_VERSION`)
- DTOs:
    - `RunManifest`
    - `TickFrame` (renderable frame contract)
    - `EventFrame`
    - `AssetPackManifest`
      **Rules**
- Pure DTOs only (dataclasses, primitives)
- Deterministic ordering (always sorted by IDs)

**Acceptance**
- `pytest`: schema round-trip JSON serialize/deserialize works
- manifest includes: world_id, episode_id, tick range, schema versions

---

### S9.2 — Export pipeline: “run → files”
**Deliverables**
- `integration/exporter.py`:
    - `export_run(history, out_dir) -> RunManifest`
    - writes:
        - `manifest.json`
        - `events.jsonl` (or chunked)
        - `frames/` (keyframes + diffs)
- clear directory layout spec

**Acceptance**
- Running a short sim produces an export folder with the correct structure
- Export is deterministic (byte-identical or logically identical with stable ordering)

---

### S9.3 — Viewer-ready frame shape from snapshots
**Deliverables**
- `integration/frame_builder.py`:
    - `build_tick_frame(world_snapshot, episode_id, tick_index) -> TickFrame`
- Minimal fields needed for viewer:
    - rooms list (id, label, neighbors, render spec placeholder)
    - agents list (id, room_id, x,y, action_state_code, render ref placeholder)
    - items list (optional minimal)

**Acceptance**
- `TickFrame` can be built for any tick without accessing runtime/narrative
- stable sort and stable float formatting policy defined (e.g., quantize to 1e-4)
## Sprint 10 — Replay Store + Scrubbing (Keyframes, Diffs, Index)

### S10.1 — Replay store format & index
**Deliverables**
- `integration/replay_store.py`:
    - `Keyframe` (full TickFrame)
    - `FrameDiff` (diff between TickFrames)
    - `ReplayIndex` (tick → offset/chunk)
- choose chunking rules:
    - keyframe every `K` ticks (config)
    - diff per tick between keyframes

**Acceptance**
- Can load a keyframe at tick T0 and apply diffs to reconstruct T1..Tn
- Index supports O(1) seek to nearest keyframe

---

### S10.2 — Generate diffs from TickFrames
**Deliverables**
- `integration/frame_diff.py`:
    - `compute_frame_diff(prev: TickFrame, curr: TickFrame) -> FrameDiff`
    - apply function: `apply_frame_diff(frame, diff) -> TickFrame`
- Only viewer-relevant diffs:
    - agent moved (room_id or x/y)
    - spawned/despawned agents/items (optional)
    - room occupancy changes (optional)

**Acceptance**
- Property test: `apply(diff(prev,curr), prev) == curr`
- Deterministic ordering inside diffs

---

### S10.3 — Exporter writes replay chunks + index
**Deliverables**
- Update `exporter.py` to:
    - write `keyframes/` + `diffs/` chunks
    - write `index.json`

**Acceptance**
- A 1,000-tick run exports quickly and loads/scrubs without replaying from tick 0

---

## Sprint 11 — Narrative → Bubble Events (Dialogue / Inner Monologue)

### S11.1 — BubbleEvent schema + mapping rules
**Deliverables**
- `integration/ui_events.py`:
    - `BubbleEvent {tick_index, duration_ticks, agent_id, room_id, kind, text, importance}`
    - `BubbleKind` enum: `DIALOGUE`, `THOUGHT`, `NARRATION`
- mapping policy doc (code comments + tests)

**Acceptance**
- Bubble events are stable and anchored (agent/room)
- No ECS/world mutation; pure transforms

---

### S11.2 — Produce bubble events from narrative outputs
**Deliverables**
- Extend runtime Phase I bridge (where StoryFragments are received) to:
    - append `BubbleEvent`s to history/export stream
- Fallback rules:
    - if no narrative, optionally generate short bubbles from structured events (like “Door opened”) — behind a flag

**Acceptance**
- Export includes `ui_events.jsonl` with bubble events
- Replay shows the same bubbles at the same ticks when using logged narrative outputs
## Sprint 12 — 2.5D Isometric “Room Map” (Render Specs)

### S12.1 — RoomRenderSpec + AgentRenderSpec + asset refs
**Deliverables**
- `integration/render_specs.py`:
    - `RoomRenderSpec {room_id, world_x, world_y, width, height, z_layer, art_ref}`
    - `AgentRenderSpec {agent_id, sprite_ref, bubble_anchor_dx, bubble_anchor_dy}`
- `AssetPackManifest` expanded with placeholder refs

**Acceptance**
- TickFrames include render specs for every room/agent (even placeholders)
- Stable positions: deterministic layout algorithm

---

### S12.2 — Deterministic layout algorithm (placeholder city map)
**Deliverables**
- `integration/layout_algos.py`:
    - if the navgraph exists: place rooms using graph layout **deterministically**
    - if navgraph stub: place rooms in a sorted order grid (guaranteed stable)

**Acceptance**
- Same world layout every run given the same identities
- No floating nondeterminism surprises (quantize coordinates)
## Sprint 13 — Psycho Topology Overlay (City-level Visualization)

### S13.1 — PsychoTopology schema
**Deliverables**
- `integration/psycho_topology.py`:
    - `PsychoTopologyFrame {tick_index, nodes[], edges[], metrics_schema_version}`
    - nodes keyed by room_id/zone_id; edges from neighbors or social ties
- Decide MVP metrics:
    - per-room: `tension_avg`, `occupancy`, maybe `mood_valence_avg`
    - per-edge: weight = (tension gradient) or adjacency strength

**Acceptance**
- Frames serialize and remain stable
- Works even if many metrics are missing (defaults)

---

### S13.2 — Builder from WorldSnapshot (+ AgentSnapshot metrics)
**Deliverables**
- `build_psycho_topology(snapshot: WorldSnapshot) -> PsychoTopologyFrame`
- sampling policy:
    - every N ticks, or scene boundary ticks only

**Acceptance**
- Export includes `psycho_topology.jsonl` (or chunked)
- Viewer can overlay without asking runtime for anything
## Sprint 14 — Godot “Reference Viewer” (minimal, proving the contracts)

### S14.1 — Loader + scrub controller
**Deliverables**
- In a `viewer_ref/` folder (or separate repo):
    - load `manifest.json`, `index.json`, keyframe/diff chunks
    - scrub slider: seek to tick, apply diffs forward/back via the nearest keyframe

**Acceptance**
- Can jump to any tick quickly
- No simulation code in viewer

---

### S14.2 — Render placeholders + bubbles + psycho overlay
**Deliverables**
- isometric-ish room rectangles / tiles (placeholder)
- agent sprites as circles/stand-ins
- bubble UI anchored to agent
- psycho overlay as heatmap tint or node graph overlay

**Acceptance**
- A recorded run “plays” visually
- Bubbles appear at correct ticks
- Psycho overlay updates on sampling ticks
## Global guardrails (Junie must enforce)
- **No layer violations**: integration reads snapshots/history only; viewer runs no sim logic.
- **Stable sorting everywhere**: rooms/agents/items/events always sorted by ID then sequence.
- **Quantize floats** at export boundary (pick one epsilon and stick to it).
- **Schema versioning**: bump only when breaking.