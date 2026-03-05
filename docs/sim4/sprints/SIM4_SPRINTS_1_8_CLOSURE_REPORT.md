# Sim4 – LLM Architect Onboarding & Godot Viewer Readiness (Post–Sprint 8)

**Status update (Feb 2026):** Bubble event export and legacy integration pipelines
described here were removed in favor of KVP-0001 exports. Treat UI-bubble export
references below as historical.

You’re coming in **after Sprints 1–8** of Sim4.  
The core substrate is in place; we now want to:

> **Finish Sim4’s architecture and connect it to a first Godot (or Godot-like) viewer:**
> - 2.5D isometric “Disco Elysium–ish” city
> - Character bubbles (dialogue + inner monologue)
> - City-level “psycho topology” visualization
> - Replay viewer (rewind, scrub, zoom timeline)

This document tells you:

1. **What exists today (Sprints 1–8)**
2. **What contracts you can rely on**
3. **What’s still missing**
4. **How ready we are for the viewer**
5. **Concrete next steps for you as the new LLM architect**

---

## 0. Layer Cake Mental Model

Sim4 is explicitly **layered** and **deterministic-first**:

- **ECS substrate (Sprints 1–2)**  
  Entities, components, archetype storage, command-driven mutations.

- **Systems & scheduler (Sprint 4)**  
  Phases B–E (Perception → Cognition → Intent → Action) exist as **skeleton systems** with queries wired, no real behavior yet.

- **World engine (Sprint 5)**  
  Data-only **WorldContext** (rooms, agents, items, doors), world commands, world events, read-only **WorldViews** façade.

- **Runtime tick (Sprint 6)**  
  Deterministic **tick()** loop that orchestrates ECS + world per phase and returns a **TickResult**.

- **Snapshot & episodes (Sprint 7)**  
  DTOs and builders for **WorldSnapshot** and **StageEpisodeV2**; snapshot diff types and episode builder.

- **Narrative runtime bridge (Sprint 8)**  
  Runtime-facing narrative DTOs, **NarrativeRuntimeContext**, and a stub **NarrativeEngineInterface** wired into tick Phase I as a sidecar.

- **Viewer layer (your remit)**
  A Godot (or Godot-like) frontend that:
    - Renders world & agents (2.5D isometric)
    - Shows narrative as bubbles/UI text
    - Visualizes psycho topology
    - Replays episodes over time

The **viewer must not break determinism** or reach into internals; it should consume **public DTOs** (snapshots, episodes, narrative outputs), not mutate the simulation.

---

## 1. Sprint 1 – ECS Core Substrate

**Goal:** Minimal ECS backbone, deterministic and Rust-portable.
### What exists

- **Entity IDs & allocator**
    - `EntityID = int`, monotonic from 1, no reuse in v1.
    - `EntityAllocator` with alive tracking (`is_alive`, `alive_ids`).

- **Archetype signatures & registry**
    - `ArchetypeSignature` = sorted tuple of component type codes.
    - `ArchetypeRegistry` maps signature ↔ `archetype_id:int`.
    - Registry manages IDs only; **storage lives in ECSWorld**.

- **Archetype SOA storage**
    - `ArchetypeStorage` with:
        - `entity_ids`, `entity_index`, `columns[type_code] -> list[Any]`.
    - Swap-remove remove semantics; deterministic for a given sequence.
    - Systems are expected to **not trust row order**; they rely on queries.

- **ECSWorld & queries**
    - `ECSWorld` with:
        - Per-world type-code mapping (`_type_to_code`, `_code_to_type`).
        - Storage registry `_storages`, entity index `_entities`.
    - Public API:
        - `create_entity(initial_components: list[object] | None)`
        - `destroy_entity(entity_id)`
        - `add_component`, `remove_component`, `get_component`, `has_component`
        - `query((CompA, CompB, ...)) -> QueryResult`
    - `QueryResult`:
        - Deterministic ordering: **ascending `EntityID`**, not storage order.
        - Each row yields `(entity_id, (components...))`.
### Why it matters for the viewer

- **Render identities:** Every agent in the viewer corresponds to an `EntityID`.
- **Stable queries:** Even if we refactor systems, queries provide deterministic views of the ECS state for snapshot building and debug UI.
- **Rust-portable:** Shapes are chosen so we can move the logic to Rust later and keep the viewer contracts stable.

---

## 2. Sprint 2 – ECS Commands & Command-Driven Mutations

**Goal:** Move from direct mutators → command-driven updates.

### What exists

- **ECSCommand & ECSCommandKind**
    - `ECSCommandKind(str, Enum)` with stable string values:
        - `"set_field"`, `"set_component"`, `"add_component"`, `"remove_component"`, `"create_entity"`, `"destroy_entity"`.
    - `ECSCommand` dataclass:
        - `seq:int`, `kind:ECSCommandKind`
        - `entity_id`, `component_type`, `component_instance`, `field_name`, `field_value` (optional fields).

- **ECSWorld.apply_commands(commands)**
    - Sorts commands by `seq` for deterministic application.
    - Implements full lifecycle:
        - `SET_COMPONENT`, `SET_FIELD`
        - `CREATE_ENTITY`, `DESTROY_ENTITY`
        - `ADD_COMPONENT`, `REMOVE_COMPONENT`
    - Fail-fast for bad commands (missing entity, missing component, missing field).
    - Deterministic no-ops for “safe” idempotent cases (destroying a missing entity, removing a non-existent component).
- **ECSCommandBuffer**
    - Systems build commands via:
        - `set_component`, `set_field`, `add_component`, `remove_component`, `create_entity`, `destroy_entity`.
    - Maintains `seq` internally; `.commands` returns a copy.
    - Tests ensure monotonic `seq` and correct wiring.

- **End-to-end ECS mini-tick tests**
    - Validate `systems → ECSCommandBuffer → ECSWorld.apply_commands` path.
    - Determinism checks across runs.

### Why it matters for the viewer

- Viewer-facing features (e.g. **time travel, replay**):
    - Rely on a **reproducible timeline** of ECS states.
    - Command-driven updates + deterministic ordering = we can reconstruct or re-simulate the same world from the same inputs.

- For future features like **debug overlays**, we can instrument command streams (e.g. show “what changed” per tick in the viewer).

---

## 3. Sprint 4 – Systems Skeleton & Scheduler

(3 is skipped here because Sprint 3 was mostly tick-path planning and gets subsumed into 4–6.)

**Goal:** Skeletonize all systems and wire a deterministic scheduler without real behavior.

### What exists

- **Systems base:**
    - `SimulationRNG`: deterministic wrapper around `random.Random`, seeded via `SystemContext`.
    - `WorldViewsHandle`: protocol for **read-only world queries** (concrete implementation is in `world/views.py`).
    - `SystemContext`:
        - Holds:
            - `world: ECSWorld`
            - `dt: float`
            - `rng: SimulationRNG`
            - `views: WorldViewsHandle`
            - `commands: ECSCommandBuffer`
            - `tick_index: int`

- **Phase B–E systems (no-op skeletons):**
    - Phase B: `PerceptionSystem`
    - Phase C: `CognitivePreprocessor`, `EmotionGradientSystem`, `DriveUpdateSystem`, `MotiveFormationSystem`, `PlanResolutionSystem`, `SocialUpdateSystem`
    - Phase D: `IntentResolverSystem`, `MovementResolutionSystem`, `InteractionResolutionSystem`, `InventorySystem`
    - Phase E: `ActionExecutionSystem`
    - Each:
        - Defines `run(self, ctx: SystemContext) -> None`
        - Declares query signatures and iterates query results.
        - Currently **does not enqueue commands** (pure scaffolding).

- **Scheduler order:**
    - `PHASE_B_SYSTEMS`, `PHASE_C_SYSTEMS`, `PHASE_D_SYSTEMS`, `PHASE_E_SYSTEMS` lists of classes in canonical order.
    - Integration tests run B→C→D→E across ticks and assert no errors.

### Why it matters for the viewer

- Systems define **where behavior will live** (perception, drives, motives, plans, action).
- For **psycho topology**, we’ll derive visual overlays from:
    - Components updated by these systems (Drives, Emotions, Motives…).
    - Snapshot DTOs that reflect their state.
- For now, logic is off—but the **attachment points** are stable.

---

## 4. Sprint 5 – World Engine Core

**Goal:** ECS-agnostic world engine: rooms, agents, items, doors, commands, events, and read-only views.

### What exists

- **WorldContext**
    - Canonical registries:
        - `rooms_by_id: dict[RoomID, RoomRecord]`
        - `agent_room: dict[AgentID, RoomID]`
        - `room_agents: dict[RoomID, set[AgentID]]`
        - `items_by_id`, `room_items`
        - `door_open: dict[DoorID, bool]`
    - Helpers:
        - `register_room`, `get_room`
        - `register_agent`, `move_agent`, `get_agent_room`, `get_room_agents`
        - `register_item`, `move_item`, `get_room_items`
        - `register_door`, `set_door_open`, `is_door_open`
    - Deterministic, ID-based, no ECS imports.

- **WorldCommand & WorldEvent**
    - `WorldCommandKind`: `set_agent_room`, `spawn_item`, `despawn_item`, `open_door`, `close_door`.
    - `WorldEventKind`: `agent_moved_room`, `item_spawned`, `item_despawned`, `door_opened`, `door_closed`.
    - Frozen dataclasses with `seq` and ID fields.

- **apply_world_commands(world_ctx, commands)**
    - Sorted by `seq`.
    - Mutates `WorldContext` and returns `list[WorldEvent]`.
    - Deterministic mapping from commands → events.

- **WorldViews & RoomView**
    - `WorldViews`:
        - `get_agent_room(agent_id) -> Optional[RoomID]`
        - `get_room_agents(room_id) -> FrozenSet[AgentID]`
        - `get_room_items(room_id) -> FrozenSet[ItemID]`
        - `is_door_open(door_id) -> bool`
        - `get_room_view(room_id) -> RoomView`
        - `iter_room_neighbors(room_id) -> Iterable[RoomID]` (currently stubbed / empty).
    - `RoomView`: frozen DTO with room id and immutable sets of agents/items.
    - `WorldContext.make_views()` returns a `WorldViews` instance (used in `SystemContext.views`).

### Why it matters for the viewer

- The viewer’s 2.5D map is primarily a **visualization of WorldContext**:
    - Rooms → tiles or zones.
    - Agents → sprites in rooms.
    - Doors → interactable edges / toggles.
- `WorldViews` gives a **stable, read-only adapter** for any debugging or live-inspector UI (e.g., an in-editor overlay that shows which agents are in which room).
- City-level visualizations (rooms + connectivity) will build on:
    - `rooms_by_id` (topology nodes)
    - `iter_room_neighbors()` once navgraph is implemented.
---

## 5. Sprint 6 – Runtime Tick Pipeline

**Goal:** Deterministic tick loop orchestrating ECS + world and exposing **TickResult**.

### What exists

- **Tick pipeline (`backend/sim4/runtime/tick.py`)**
    - Phases:
        - A: Input (stub for now)
        - B–D: Systems (via scheduler; uses `SystemContext`)
        - E: ECS apply (via `ECSCommandBatch` + `world.apply_commands`)
        - F: World apply (via `WorldCommandBatch` + `apply_world_commands`)
        - G: Event consolidation → `RuntimeEvent`
        - H: History (stub; snapshot integration happens here conceptually)
        - I: Narrative (now wired in Sprint 8)
    - Returns a **TickResult**:
        - Contains at least time/tick index and aggregated runtime events.
        - Designed for history, snapshotting, and later replay.

- **Command batches**
    - `ECSCommandBatch`, `WorldCommandBatch`:
        - Provide global per-tick sequence indices for deterministic ordering.
        - Sponsor the **“no hidden randomness”** rule.

- **RuntimeEvent & consolidation**
    - Wraps world events and (later) ECS events into a common envelope.
    - Records event origin and per-tick order.
### Why it matters for the viewer

- **Replay viewer** is built on:
    - Running the deterministic tick loop.
    - **Recording snapshots/episodes** (Sprint 7).
    - Replaying them either by re-simulating from initial conditions, or by loading stored `StageEpisodeV2` files.
- The Godot viewer should treat `tick()` as the **single source of truth** for simulation steps, and treat `TickResult` / snapshots as read-only.

---

## 6. Sprint 7 – Snapshot & Episode

**Goal:** DTOs and builders for world snapshots and episodes; define the canonical “timeline” representation.

### What exists (implemented)

- **Snapshot DTOs (`world_snapshot.py`)**
    - `WorldSnapshot`:
        - Per-tick snapshot of:
            - Rooms (from WorldContext)
            - Agents (from ECSWorld)
            - Items (world-side)
            - Key components (e.g., Transform, RoomPresence; ActionState/NarrativeState references if present).
        - Deterministic ordering: rooms and agents sorted by ID.
        - Lookup maps: `room_index`, `agent_index` (dicts mapping ID → index).

    - Nested DTOs (frozen, primitives-only):
        - `RoomSnapshot`
        - `AgentSnapshot` (+ sub-DTOs):
            - `TransformSnapshot`
            - `AgentSocialSnapshot`
            - `MotiveSnapshot`
            - `PlanSnapshot` / `PlanStepSnapshot`
        - `ItemSnapshot`

- **Episode DTOs (`episode_types.py`)**
    - UI-facing episode structures:
        - `EpisodeMeta`
        - `EpisodeMood`
        - `SceneSnapshot`
        - `TensionSample`
        - `DayWithScenes`
        - `StageEpisodeV2`
        - `EpisodeNarrativeFragment`
    - These are **front-end oriented**: StageEpisode is what a viewer / replay tool should ingest.

- **WorldSnapshot builder (`world_snapshot_builder.py`)**
    - `build_world_snapshot(tick_index, episode_id, world_ctx, ecs_world) -> WorldSnapshot`
    - Minimal implemented behavior (deterministic, read-only):
        - Builds rooms (occupants/items/neighbors), agents, and items from engine state.
        - Explicit sorting for determinism; no RNG/time; no mutations.
        - Requires `Transform` + `RoomPresence` for agents; treats `ActionState` / `NarrativeState` as optional.

- **Episode builder (`episode_builder.py`)**
    - Functions:
        - `start_new_episode(...) -> StageEpisodeV2`
        - `append_tick_to_episode(episode, world_snapshot, ...)`
        - `finalize_episode(episode)`
    - Implemented behavior (bookkeeping only):
        - `start_new_episode`: seeds `EpisodeMeta` (empty title/synopsis), sets `tick_start = tick_end = initial`, `duration_seconds = 0.0`; `days=[]`; `key_world_snapshots=[initial_snapshot]`.
        - `append_tick_to_episode`: appends `world_snapshot`, extends `narrative_fragments`, updates `meta.tick_end`, and sets `duration_seconds = tick_end - tick_start`.
        - `finalize_episode`: no-op for Sprint 7.
        - No tension/mood aggregation; no scene/day segmentation in Sprint 7 (days remain empty).

- **Snapshot diff (`diff_types.py`, `snapshot_diff.py`)**
    - DTOs: `SnapshotDiff`, `AgentDiff`, `RoomOccupancyDiff`, `ItemDiff` (frozen, primitives-only).
    - Builder: `compute_snapshot_diff(prev, curr) -> SnapshotDiff`
        - Detects agent room changes and position changes, room entries/exits, and item spawn/despawn/moves.
    - Summarizer: `summarize_diff_for_narrative(diff) -> dict`
        - Produces compact JSON-like dict: `moved_agents`, `room_entries`, `room_exits`, `spawned_items`, `despawned_items`.
    - Used by Sprint 8 narrative to summarize changes.

- **Snapshot API surface**
    - `sim4.snapshot` exports:
        - `build_world_snapshot`
        - `start_new_episode`, `append_tick_to_episode`, `finalize_episode`
        - `WorldSnapshot`, `StageEpisodeV2`, `SnapshotDiff`,
        - `compute_snapshot_diff`, `summarize_diff_for_narrative`, and related diff DTOs.

### Why it matters for the viewer

- **StageEpisodeV2 is the canonical replay timeline**:
    - Godot viewer can load `StageEpisodeV2` (e.g., from JSON) and:
        - Scrub through ticks.
        - Reconstruct positions, rooms, and states of agents.
        - Layer narrative fragments onto scenes.
- **SnapshotDiff** supports:
    - Efficient playback (“only change these entities/rooms since last frame”).
    - Visual hints (e.g., highlight rooms/agents that changed in psycho topology view).

---
## 7. Sprint 8 – Narrative Runtime Bridge (Current Sprint)

**Goal:** Introduce runtime-facing narrative DTOs, runtime context, and Phase I tick wiring — *without real LLM logic yet*.

### What exists

- **Narrative DTOs (`runtime/narrative_context.py`)**
    - Types (as per SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT §4):
        - `NarrativeBudget` / `NarrativeBudgetConfig`
        - `NarrativeTickContext`
        - `NarrativeTickOutput`
        - `SubstrateSuggestion`
        - `StoryFragment`
        - `MemoryUpdate`
        - `NarrativeEpisodeContext`
        - `NarrativeEpisodeOutput`
        - `NarrativeUICallContext`
        - `NarrativeUIText`
    - Key idea:
        - **Runtime owns these DTOs.**  
          Narrative engines consume them and return outputs, but do **not** reach into ECS/world directly.

- **NarrativeEngineInterface & NullNarrativeEngine (`narrative/interface.py`)**
    - `NarrativeEngineInterface`:
        - Methods like `run_tick_jobs(...)`, `summarize_episode(...)`, `describe_scene(...)`.
    - `NullNarrativeEngine`:
        - Stub implementation with deterministic, trivial outputs (non-empty text to keep tests happy).
        - **No network / LLM / I/O / RNG**.
- **NarrativeRuntimeContext (`runtime/narrative_context.py`)**
    - Bridge between runtime tick and narrative engine:
        - `build_tick_context(tick_index, dt, episode_id, world_ctx, ecs_world, history) -> NarrativeTickContext`
            - Builds `WorldSnapshot` (or equivalent view).
            - Pulls `diff_summary` from history (computed via `SnapshotDiff(prev, curr)` summarization).
            - Constructs `NarrativeBudget` from `NarrativeBudgetConfig` and tick metadata.
        - `run_tick_narrative(...)`:
            - Applies stride/enable gating.
            - Calls `engine.run_tick_jobs(NarrativeTickContext)`.
            - Logs outputs into history (no ECS/world mutation).

- **Tick integration (Phase I)**
    - `tick()` now accepts:
        - `episode_id` (optional)
        - `narrative_ctx: Optional[NarrativeRuntimeContext]`
    - After Phase H (history), Phase I:
        - Calls `narrative_ctx.run_tick_narrative(...)` if provided.
        - Wrapped in `try/except` so narrative failures never crash simulation core.

- **SOT & docs updated**
    - `SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT.md`:
        - **Status — Sprint 8**: describes what’s implemented & what’s deferred.
    - `2025-12-01_sim4_ecs_implementation_overview.md`:
        - Adds “Sprint 8 – Narrative Runtime Bridge & Stubs” section.

### Why it matters for the viewer

- **Character bubbles & UI text**:
    - Will be generated as `StoryFragment` and/or `NarrativeUIText` records from the narrative engine.  
    - Viewer does not talk to LLM directly; it consumes these DTOs (possibly via StageEpisode / EpisodeNarrativeFragment or per-tick streams).
- **Psycho topology overlays**:
    - Narrative engine can compute higher-level interpretations (e.g., “tension in this district”, “agent X is anxious”) given snapshots + diff summaries.
    - Viewer can then render **layered visualizations** based on:
        - Raw ECS/WorldSnapshot state, plus
        - Narrative summarizations derived from `diff_summary`, `StoryFragment`, `SubstrateSuggestion`, etc.
- **Replay viewer**:
    - Narrative outputs logged in history per tick can be folded into StageEpisode scenes and thus appear in replays without re-calling LLMs.

---

## 8. Readiness for the Godot / Viewer Features

Now, map the requested viewer features to current readiness.

### 8.1 2.5D Isometric (Disco Elysium vibe)

**What we already have:**

- IDs and structural data:
    - `WorldContext` for rooms/agents/items/doors.
    - `WorldSnapshot` & `StageEpisodeV2` for per-tick state.
- Deterministic positions:
    - `Transform` components (in ECS) → position/rotation per agent.
    - `RoomPresence` → which room an agent is in.
- Deterministic time:
    - `TickClock`, tick indices, snapshot per tick.

**What’s missing / to be defined:**

- **Geometry and layout**:
    - Rooms currently are ID + metadata, no world-space coordinates.
    - Need a mapping from `RoomID` → `(x,y)` (and maybe z-level) for isometric projection.
- **Navgraph / neighbors**:
    - `iter_room_neighbors()` is stubbed.
    - City topology is conceptual, not implemented.
- **Asset / rendering metadata**:
    - No component yet that says “Agent X uses sprite Y, animation set Z”.
    - Viewer must layer its own asset mapping over canonical ids.

**Readiness level:**  
Backend is **ready enough** to power a minimal 2.5D viewer if you:

- Define a first **RoomLayout config** (static mapping from room ID → tile coordinates).
- Use `WorldSnapshot` agent positions and `RoomPresence` to place sprites.
- Accept that navgraph + complex navigation are future work.

---

### 8.2 Character Bubbles (Dialogue / Inner Monologue)

**What we already have:**

- DTOs for narrative messages:
    - `StoryFragment`: textual narrative chunks tied to agents/scenes.
    - `NarrativeUIText`: explicit UI-facing text (e.g., tooltip, subtitle).
- Narrative runtime bridge:
    - `NarrativeTickContext` contains snapshots + diff summaries + space for budgets.
    - `NarrativeTickOutput` can be extended to include per-agent text.
      **What’s missing:**

- **Real narrative engine**:
    - `NullNarrativeEngine` is a stub; no actual story content.
- **Binding to episodes**:
    - We need a clear pipeline:
        - `NarrativeTickOutput` → `EpisodeNarrativeFragment` → StageEpisode scenes.
- **Viewer protocol**:
    - For online mode: the viewer needs a contract like:
        - “For tick T, give me all UI texts relevant to agents visible in viewport”.

**Readiness level:**  
Structurally, we’re ready:

- Types exist.
- Runtime hook into Phase I exists.

We now need you to:

- Design and eventually implement the **first non-trivial NarrativeEngine**.
- Define the **mapping from `StoryFragment` / `NarrativeUIText` → viewer bubble rendering schema** (JSON, gRPC, whatever).
- Start with **debug-friendly text** (e.g., "Agent 3 moved from Room 1 to Room 2") before going full LLM-prose.

---

### 8.3 City-Level Visualization of “Psycho Topology”
Think of it as a **heatmap of psyche & social tension across rooms/city districts**.

**What we already have:**

- Substrate & snapshot shapes for “inner state”:
    - Systems scaffolding includes components for Drives, Emotions, Motives, Social substate, Plans, etc. (even if logic is off).
    - Snapshot DTOs (AgentSocialSnapshot, MotiveSnapshot, PlanSnapshot…) are defined.
- World topology primitives:
    - Rooms, agents, and (stub) neighbors.
- Narrative diff pipeline:
    - `SnapshotDiff` and `diff_summary` exist as the input to narrative.
    - Narrative can compute derived metrics (“tension”, “cohesion”, “isolation”).

**What’s missing:**

- **Real system logic**:
    - Drives, motives, social graphs are not being meaningfully updated yet.
- **Aggregation semantics**:
    - We need definitions like:
        - `room_tension(room_id) ∝ aggregate(f(agent.drives, agent.emotions, interactions))`
- **Viewer overlay spec**:
    - E.g., for each room:
        - color value (hue/intensity)
        - one or more metrics (tension, comfort, chaos, etc.)
    - For each agent:
        - glyph overlays (icons, small bars).

**Readiness level:**  
Conceptually aligned but **requires your design**:

- At first, use simple **derived metrics**:
    - e.g. count of agents in conflict, or dummy “mood” values from NarrativeEngine.
- Later, enforce a stable schema:
    - `PsychoTopologySnapshot` (per tick) mapping rooms/agents → metrics
    - consumed by viewer for overlays.

---

### 8.4 Replay Viewer (Rewind, Zoom Timeline)

**What we already have:**

- Deterministic tick engine.
- Snapshot DTOs (`WorldSnapshot`) and Episode DTO (`StageEpisodeV2`).
- Minimal Episode builder.
- Snapshot diff types.
- Narrative runtime sidecar that can log narrative outputs per tick into history.

**What’s missing:**

- Full **history layer**:
    - Phase H is still conceptually “history” but not a full module yet.
    - Need explicit persistence: storing snapshots, diffs, and narrative outputs.
- Export / import format:
    - Stable JSON (or similar) representation for `StageEpisodeV2` suitable for Godot.
- Viewer controls:
    - UI timeline, scrubbing semantics, etc.
      **Readiness level:**  
      Backend is **very close** to ready:

- You can already:
    - Run a short simulation.
    - Build snapshots and an episode.
    - Serialize the episode to JSON.
- A first replay viewer can load an episode file and:
    - Step through snapshots.
    - Render positions and simple overlays.
    - Show narrative text if present.

---

## 9. Next Steps for You (LLM Architect Roadmap)

Here’s a concrete roadmap for your role.

### Phase 0 – Absorb & Align

1. **Read the key SOTs**:
    - `SOT-SIM4-ECS-CORE`
    - `SOT-SIM4-WORLD-ENGINE`
    - `SOT-SIM4-SNAPSHOT-AND-EPISODE`
    - `SOT-SIM4-RUNTIME-TICK`
    - `SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT`
2. Skim implementation reports for Sprints 1–8 (already summarized here).
3. Build a **mental model** of:
    - ECS ↔ systems ↔ world ↔ runtime tick ↔ snapshot ↔ narrative.

### Phase 1 – Canonical Viewer Contracts

Design explicit **viewer-facing DTOs / APIs** on top of existing ones:

- **RenderFrameDTO or ViewerTickFrame**
    - Derived from `WorldSnapshot` (+ possibly SnapshotDiff).
    - Contains:
        - Room positions (from static layout config)
        - Agent positions and IDs
        - Door states
        - Optional overlays (psycho metrics, narrative markers)
- **Timeline / Episode DTO**
    - Choose whether viewer consumes:
        - Raw `StageEpisodeV2` directly, or
        - A flattened `ViewerEpisode` DTO optimized for Godot.

Keep it **read-only and deterministic**; no viewer writes back into simulation.

### Phase 2 – Minimal Replay Viewer Integration

1. Implement a small **exporter**:
    - Run a test scenario.
    - Build `StageEpisodeV2`.
    - Export to JSON (or similar).
2. In Godot (or similar engine):
    - Build a tiny scene that:
        - Loads the episode file.
        - Maps rooms to tiles (hardcoded layout).
        - Draws agents as colored circles.
        - Adds a simple scrubber UI to step through ticks.

This gives us an **end-to-end vertical slice**: Sim4 → JSON → Viewer.

### Phase 3 – Narrative & Bubbles v0

1. Extend `NarrativeEngineInterface` beyond `NullNarrativeEngine`:
    - **First implementation (non-LLM, deterministic)**:
        - For each tick, emit `StoryFragment`s like:
            - “Agent 3 moved from Room 1 to Room 2.”
            - “Agent 5 picked up Item 2.”
    - Use `SnapshotDiff` + `diff_summary` to drive this.
2. Inject these into:
    - Either `NarrativeTickOutput` directly, or
    - `EpisodeNarrativeFragment` and attach to StageEpisode scenes.
3. Viewer:
    - For the current tick, show speech bubbles above agents based on `StoryFragment`s.

This yields **baseline, debuggable bubbles** before any LLM involvement.

### Phase 4 – Psycho Topology v0

1. Define a **PsychoTopology model**:
    - For the first version:
        - Room “intensity” = number of agents + movement frequency.
        - Agent “stress” = simple synthetic function (e.g., number of moves + interactions).
2. Emit per-tick `PsychoTopologySnapshot` from either:
    - A dedicated system, or
    - Narrative engine using snapshots/diffs.
3. Viewer:
    - Color rooms based on intensity.
    - Show small bars/icons above agents for “stress”.

Later, you can let an LLM-driven NarrativeEngine push more nuanced metrics.

### Phase 5 – LLM Narrative Engine Prototype

Once the pipes are stable:

1. Design a **prompting and schema strategy** for `NarrativeEngineInterface`:
    - LLM receives:
        - `NarrativeTickContext` (or a distilled JSON view of it).
        - `diff_summary`.
        - Episode meta so far.
    - LLM returns:
        - List of `StoryFragment`s and/or `NarrativeUIText` entries.
        - Optional suggestions (`SubstrateSuggestion`) for future behavior.
2. Keep **bridge layer deterministic**:
    - Narrative outputs are stochastic, but:
        - The LLM call is isolated.
        - The rest of the system remains deterministic given those outputs.
3. Decide on **online vs offline**:
    - Online mode: viewer shows LLM text as simulation runs.
    - Offline mode: narrative is precomputed and baked into StageEpisode files.

---

## 10. Core Principles to Preserve

As you design the remaining architecture and viewer integration, keep these invariants:

1. **Determinism of the core simulation**  
   Narrative & viewer are sidecars. Simulation state is a pure function of input events + seeds, not LLM sampling.

2. **Layer purity**
    - ECS never imports world or narrative.
    - World never imports ECS or narrative.
    - Runtime orchestrates, but doesn’t implement semantics.
    - Narrative consumes snapshots/DTOs, returns DTOs — no direct mutations.
    - Viewer consumes public DTOs — no direct access to internal state.

3. **Rust-portable shapes**
    - DTOs are kept simple: ints, floats, strings, booleans, lists, dicts.
    - No Python-only magic in public contracts.

4. **Replay-first mindset**
    - Anything rendered in the viewer should be reconstructible from:
        - Seed + inputs, OR
        - A stored `StageEpisodeV2` + narrative fragments.

---

If you internalize this doc, you should be able to:

- Reason about where to add new DTOs without breaking layering.
- Design viewer-facing APIs that sit cleanly on top of snapshots/episodes.
- Grow the narrative engine from a stub into a meaningful LLM-driven storyteller.
- Ship a first Godot prototype that **replays** Sim4 worlds with:
    - 2.5D agents and rooms,
    - simple psycho topology overlays,
    - and basic narrative bubbles — all powered by the architecture we already have.
