# 🌐 SIM4 — Engine Spec (v1.0, SOP-Aligned)
_**Python prototype, Rust-aligned, SimX-ready**_  
Aligned with:
* **SIMX Vision**
* **Free Agent Spec**
* **SOP-000** Architect Operating Contract
* **SOP-100** Layer Boundary Protection
* **SOP-200** Determinism & Simulation Contract
* **SOP-300** ECS Specification & Agent Substrate Architecture
---

## 0. High-Level Design

Sim4 is a **dual-engine architecture**:

**1. Deterministic Kernel (Simulation Core)**
* `runtime/`, `ecs/`, `world/`
* deterministic, Rust-portable, replayable
* holds **substrates** for the 7-layer agent mind (L1 – L5, plus L7 numeric vectors)

**2. Narrative Mind Engine (Sidecar)**
* `narrative/`
* nondeterministic meaning-making (LLM-side), but **contracted outputs**
* reads snapshots / diffs / curated runtime context
* produces semantic narrative state + intent/goal suggestions, materialized only via **Phase A integration** and sanitized before the next tick

**3. Presentation & IO Layers**
* `snapshot/`, `integration/`
* read-only views + export schemas for viewers (Godot/Web/etc.)
* no simulation logic; no kernel mutation

The **six-layer DAG** of SOP-100 is preserved:

```text
Kernel:   runtime → ecs → world
                \         \
                 \         → snapshot → integration
                  \
                   → (read-only views) → narrative
narrative → (suggestion queues) → runtime (Phase A integration ONLY)
```

And the **7-layer agent mind** from SOP-300 + Free Agent Spec is realized as:
* Substrate in ECS: L1–L5 + numeric L7
* Semantic in Narrative: L3–L7


---

## 1. Final Folder Structure (v1.0 — Implemented Reality)

This section is the **canonical structure** as it exists under `backend/sim4/` today.

```text
backend/sim4/
   ├── runtime/                          # SOP-200 tick pipeline + orchestration glue (kernel)
   │   ├── tick.py                       # canonical tick() implementation (phases A–I)
   │   ├── scheduler.py                  # PhaseScheduler (SOP-200 phases + system execution)
   │   ├── clock.py                      # TickClock / DeltaTime utilities
   │   ├── command_bus.py                # command routing + application coordination
   │   ├── events.py                     # runtime-level events + consolidation helpers
   │   ├── narrative_context.py          # builds NarrativeContext from snapshots/diffs/events
   │   └── bubble_bridge.py              # narrative bubbles → integration ui_events
   │
   ├── ecs/                              # ECS core (Rust-portable deterministic substrate)
   │   ├── world.py                      # ECSWorld — storage + apply_commands
   │   ├── entity.py                     # EntityID allocation + registry helpers
   │   ├── storage.py                    # SOA/archetype-like storage backend
   │   ├── archetype.py                  # archetype definitions & layout rules
   │   ├── query.py                      # ECS query engine (read/write views)
   │   ├── commands.py                   # ECSCommand + command buffer primitives
   │   ├── components/                   # Agent + world-substrate components
   │   │   ├── identity.py               # SelfModelSubstrate / identity vectors
   │   │   ├── embodiment.py             # Transform / Velocity / RoomPresence / PathState
   │   │   ├── perception.py             # PerceptionSubstrate (visibility/salience/attention)
   │   │   ├── belief.py                 # BeliefGraphSubstrate / inference weights
   │   │   ├── drives.py                 # DriveState (curiosity/safety/attachment/etc.)
   │   │   ├── emotion.py                # EmotionFields (tension/mood drift/charge/etc.)
   │   │   ├── social.py                 # SocialSubstrate (trust/relationship/factions/etc.)
   │   │   ├── motive_plan.py            # MotiveSubstrate + PlanLayerSubstrate
   │   │   ├── intent_action.py          # PrimitiveIntent / SanitizedIntent / ActionState
   │   │   ├── inventory.py              # InventorySubstrate (IDs only)
   │   │   ├── narrative_state.py        # NarrativeState (semantic refs only; LLM-owned)
   │   │   └── meta.py                   # Debug flags, system markers, tags
   │   └── systems/                      # Deterministic systems (SOP-300 §7)
   │       ├── base.py
   │       ├── scheduler_order.py        # explicit mapping: systems → SOP-200 phases
   │       ├── perception_system.py
   │       ├── cognitive_preprocessor.py
   │       ├── emotion_gradient_system.py
   │       ├── drive_update_system.py
   │       ├── motive_formation_system.py
   │       ├── plan_resolution_system.py
   │       ├── intent_resolver_system.py
   │       ├── movement_resolution_system.py
   │       ├── interaction_resolution_system.py
   │       ├── social_update_system.py
   │       ├── action_execution_system.py
   │       └── inventory_system.py
   │
   ├── world/                            # Deterministic world engine (SOP-100/200)
   │   ├── context.py                    # WorldContext (world façade; no ECS imports)
   │   ├── views.py                      # WorldViews (read-only projections for ECS/snapshot)
   │   ├── commands.py                   # WorldCommand types
   │   ├── events.py                     # WorldEvent types
   │   └── apply_world_commands.py       # deterministic command application (Phase F)
   │
   ├── snapshot/                         # Deterministic snapshots + diffs + episode assembly
   │   ├── world_snapshot.py             # WorldSnapshot / AgentSnapshot / RoomSnapshot / ItemSnapshot DTOs
   │   ├── world_snapshot_builder.py     # builds snapshots from ECS + world (Phase H)
   │   ├── snapshot_diff.py              # snapshot diff computation
   │   ├── diff_types.py                 # diff DTOs and stable structures
   │   ├── episode_types.py              # Episode DTOs (semantic-safe containers)
   │   └── episode_builder.py            # Episode builder (snapshot stream → episode)
   │
   ├── narrative/                        # Narrative sidecar contract surface (minimal by design)
   │   └── interface.py                  # DTOs + interface contract for narrative engine integration
   │
   ├── integration/                      # IO/export schemas + deterministic serialization
   │   ├── schema/                       # canonical frame schemas + versioning
   │   │   ├── version.py
   │   │   ├── run_manifest.py
   │   │   ├── tick_frame.py
   │   │   ├── room_frame.py
   │   │   ├── agent_frame.py
   │   │   ├── item_frame.py
   │   │   └── event_frame.py
   │   ├── adapters/
   │   │   └── snapshot_adapter.py       # snapshot → integration frames
   │   ├── frame_builder.py              # builds TickFrame from snapshots/events
   │   ├── frame_diff.py                 # deterministic diffs for client streaming
   │   ├── ui_events.py                  # UI event schema (bubble events, etc.)
   │   ├── exporter.py                   # writes runs: manifest + frames + ui events
   │   ├── types.py
   │   ├── util/
   │   │   ├── stable_json.py            # stable JSON serialization
   │   │   ├── stable_hash.py            # stable hashing primitives
   │   │   └── quantize.py               # quantization helpers for stable numeric export
   │   └── tests/                        # integration export correctness + replay tests
   │
   └── tests/                            # end-to-end and unit tests across layers
       ├── ecs/...
       ├── world/...
       ├── snapshot/...
       ├── runtime/...
       └── narrative/...
```

**Key structural corrections vs the old v1.0 spec**
- `runtime/engine.py`, `runtime/diff.py`, `runtime/history.py`, `runtime/replay.py`, `runtime/world_context.py`, `runtime/episode.py` do not exist in this repo layout.
  - The real orchestrator is `runtime/tick.py` + `runtime/scheduler.py` + `runtime/command_bus.py`.
- `snapshot/` is not `builder.py/schema.py/serializer.py/diff_adapter.py`; it is:
  - `world_snapshot.py`, `world_snapshot_builder.py`, plus **diff** + **episode** modules.
- `narrative/` is **not** the big generator/pipeline/memory stack here.
  - It is currently a **contract-first interface** module: `narrative/interface.py`.
- `world/` is **flattened** into `context/views/commands/events/apply_world_commands` (no identity/graph/layout subfolders in this snapshot).
- `integration/` is **schema** + **exporter** + **frame builders** + **diffs** + **ui events** + **stable util**, with strong test coverage.

---

## 2. Mapping to the 7-Layer Agent Mind

From SOP-300 + Free Agent Spec:

```text
L1 — Embodied & Raw Perception Layer
L2 — Perception & Attention Layer
L3 — Belief, Concept & Self-Model Layer
L4 — Drives & Emotion Fields Layer
L5 — Motives & Planning Layer
L6 — Reflection Layer
L7 — Narrative & Persona/Aesthetic Mind
```

---

### 2.1 Substrate Components in ECS (Implemented)
#### L1 — Embodied & Raw Perception
- `ecs/components/embodiment.py`
  - `Transform`
  - `Velocity`
  - `RoomPresence`
  - `PathState`
- `ecs/components/perception.py`
  - raw sensory lists / perceived entities
  - attention hooks

#### L2 — Perception & Attention
- `ecs/components/perception.py`
  - salience scores
  - attention slots
  - perceptual flags

#### L3 — Belief, Concept & Self-Model
- `ecs/components/identity.py`
  - `SelfModelSubstrate`
- `ecs/components/belief.py`
  - `BeliefGraphSubstrate`
  - inference state / weights

#### L4 — Drives & Emotion Fields
- `ecs/components/drives.py` — DriveState
- `ecs/components/emotion.py` — EmotionFields

#### L5 — Motives & Planning
- `ecs/components/motive_plan.py`
  - `MotiveSubstrate`
  - `PlanLayerSubstrate`
- `ecs/components/intent_action.py`
  - `PrimitiveIntent`
  - `SanitizedIntent`
  - `ActionState`

#### L6 — Reflection (Semantic Only)
- Lives in the narrative sidecar domain.
- In this repo, the boundary is expressed via **DTOs/contracts** in  
`narrative/interface.py` and contexts built in `runtime/narrative_context.py`.

#### L7 — Narrative & Persona/Aesthetic
- Numeric substrate (optional / evolving) can live in `identity.py` or future dedicated components.
- Semantic narrative artifacts are exported as **ui_events** via:
  - `runtime/bubble_bridge.py` → `integration/ui_events.py`

---

## 3. Tick & Determinism (SOP-200 Alignment)

### 3.1 Canonical Tick (Implemented in `runtime/tick.py`)
The canonical SOP-200 phase model is implemented as a tick pipeline, with these phases remaining the “contract shape”:

```text
tick(dt):
    Phase A: Input Processing & Adapters (incl narrative suggestion integration)
    Phase B: Perception systems
    Phase C: Deterministic cognition/drive/emotion/social systems
    Phase D: Intent resolution → command emission (sanitize)
    Phase E: ECS apply_commands (ECS-only mutation)
    Phase F: World apply_world_commands (world-only mutation)
    Phase G: Event consolidation (runtime)
    Phase H: Snapshot build + diff + episode hooks + export
    Phase I: Narrative trigger (sidecar; no kernel mutation)
```

**Where it lives now**
- Phase scheduling / system execution: `runtime/scheduler.py` + `ecs/systems/scheduler_order.py`
- Command routing/application: `runtime/command_bus.py` + `ecs/commands.py` + `world/apply_world_commands.py`
- Runtime event consolidation: `runtime/events.py` (plus world events)
- Snapshot build + diff + episode: `snapshot/world_snapshot_builder.py`, `snapshot/snapshot_diff.py`, `snapshot/episode_builder.py`
- Narrative context + integration to UI events: `runtime/narrative_context.py` + `runtime/bubble_bridge.py`

---

### 3.2 Determinism Rules
- Kernel mutation happens **only** in:
  - Phase E: ECS `apply_commands` (inside `ecs/world.py` / command buffer logic)
  - Phase F: World `apply_world_commands` (`world/apply_world_commands.py`)
- Phase ordering is explicit and stable; system order is pinned in `ecs/systems/scheduler_order.py`.
- Any export output uses deterministic encoders:
  - `integration/util/stable_json.py`
  - stable hashing `stable_hash.py`
  - numeric export stability `quantize.py`

---

## 4. ECS Systems (Concrete Mapping to SOP-300)

Systems present in `ecs/systems/` (as implemented) and their intended phase mapping:

1. **PerceptionSystem** (`perception_system.py`) — Phase B  
2. **CognitivePreprocessor** (`cognitive_preprocessor.py`) — Phase C  
3. **EmotionGradientSystem** (`emotion_gradient_system.py`) — Phase C  
4. **DriveUpdateSystem** (`drive_update_system.py`) — Phase C  
5. **MotiveFormationSystem** (`motive_formation_system.py`) — Phase C  
6. **PlanResolutionSystem** (`plan_resolution_system.py`) — Phase C  
7. **IntentResolverSystem** (`intent_resolver_system.py`) — Phase D  
8. **MovementResolutionSystem** (`movement_resolution_system.py`) — Phase D  
9. **InteractionResolutionSystem** (`interaction_resolution_system.py`) — Phase D  
10. **SocialUpdateSystem** (`social_update_system.py`) — Phase C  
11. **ActionExecutionSystem** (`action_execution_system.py`) — Phase E  
12. **InventorySystem** (`inventory_system.py`) — Phase E (optional substrate)

**Hard rule preserved:** ECS systems do **not** import `world/` directly. World information arrives via runtime-provided views (`world/views.py`) or adapters in the execution harness.

---

## 5. World Layer (SOP-100 & SOP-200)

`world/` is the deterministic environment core:

* `world/context.py` — authoritative world façade (no ECS imports)
* `world/views.py` — read-only projections for ECS/snapshot/integration
* `world/commands.py` — structured world commands
* `world/events.py` — structured world events
* `world/apply_world_commands.py` — deterministic applier (Phase F)

World mutations happen **only** in Phase F via world commands.

---

## 6. Narrative Layer (Sidecar, SOP-100/SOP-300)

In this repo, narrative is intentionally **contract-first**:

* `narrative/interface.py` defines:
  * DTOs for narrative inputs/outputs (what runtime may send; what narrative may return)
  * the allowed “surface area” of narrative influence (suggestions only)

Runtime prepares narrative inputs via:
* `runtime/narrative_context.py`

Runtime converts narrative outputs to presentation artifacts via:
* `runtime/bubble_bridge.py` → integration `ui_events.py`

Narrative may **not**:
* mutate ECS/world directly
* bypass Phase A integration/sanitization
* affect tick timing

---

## 7. Snapshot & Integration

### 7.1 Snapshot (Deterministic Views)
`snapshot/` is the canonical view + episode assembly layer:
* `world_snapshot.py` + `world_snapshot_builder.py`
* diffs: `snapshot_diff.py` + `diff_types.py`
* episodes: `episode_types.py` + `episode_builder.py`

Snapshots and diffs are deterministic outputs of the kernel state.

### 7.2 Integration (IO / Export)
`integration/` is stable export + schemas + tooling:
* frame schemas: `integration/schema/*`
* build frames: `frame_builder.py` + adapter `adapters/snapshot_adapter.py`
* diffs: `frame_diff.py`
* UI events: `ui_events.py`
* exporter: `exporter.py`
* determinism helpers: `util/stable_json.py`, `util/stable_hash.py`, `util/quantize.py`

Integration is IO-only: no simulation mutations.

---

## 8. SOP & SOT Library (SOPs + Free Agent Spec)

### SOPs (Behavior / Rules)
**1. SOP-000 — Architect Operating Contract (AOC)**
* Defines how Architect-GPT behaves.
* Guards long-arc coherence, anti-drift, version stability.
**2. SOP-100 — Layer Boundary Protection**
* Six-layer DAG (runtime/ecs/world/snapshot/integration + narrative sidecar).
* Defines allowed/forbidden dependencies and mutation layers.
**3. SOP-200 — Determinism & Simulation Contract**
* Tick phases, RNG rules, ordering, diff & replay.
**4. SOP-300 — ECS Specification & Agent Substrate Architecture**
* 7-layer mind mapping to ECS substrate.
* Canonical components, systems, and substrate vs semantic split.
* Movement & interaction pipeline.

### SOTs (Architecture / Specs)
* **SimX Vision** — long-arc design target (emergent narrative city).
* **Free Agent Spec** — defines agent mind entities:
  * `SelfModel`, `ConceptGraph`, `BeliefState`, `DriveState`,  
  `MotiveSystem`, `PlanLayer`, `ReflectionState`, `SocialMind`, `AestheticMind`.
* **SOT-SIM4-ENGINE** (this doc) — folder structure, layer responsibilities, system mapping.
* Future SOTs can specialize (e.g. `SOT-WORLD-IDENTITY`, `SOT-EPISODE-OUTPUT`), but must obey the SOPs.
* Current SOTs:
  * Sim4 engine overview:
      * SOT-SIM4-ENGINE v1.0
  * ECS:
    * SOT-SIM4-ECS-COMMANDS-AND-EVENTS
      SOT-SIM4-ECS-CORE
      SOT-SIM4-ECS-SUBSTRATE-COMPONENTS-DETAILS
      SOT-SIM4-ECS-SUBSTRATE-COMPONENTS
      SOT-SIM4-ECS-SYSTEMS
  * Runtime:
    * SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT
    * SOT-SIM4-RUNTIME-TICK
    * SOT-SIM4-RUNTIME-WORLDCONTEXT
  * World:
    * SOT-SIM4-WORLD-ENGINE
  * Narrative:
    * docs/sim4/SOTs/SOT-SIM4-NARRATIVE-INTERFACE
  * Snapshots & Diffs:
    * docs/sim4/SOTs/SOT-SIM4-SNAPSHOT-AND-EPISODE

### Short Table
| Type | 	Name                   | 	Role                                  |
|------|-------------------------|----------------------------------------|
| SOP  | 	SOP-000                | 	Architect behavior, anti-drift        |
| SOP  | 	SOP-100                | 	Layer boundaries, DAG, mutation rules |
| SOP  | 	SOP-200                | 	Determinism, tick, RNG, replay        |
| SOP  | 	SOP-300                | 	ECS substrate & 7-layer mind mapping  |
| SOT  | 	SimX Vision            | 	Long-arc target                       |
| SOT  | 	Free Agent Spec        | 	Agent mind definition                 |
| SOT  | 	SOT-SIM4-ENGINE (this) | 	Concrete Sim4 engine architecture     |

## 9. Completion Condition for Sim4 Engine Spec (Updated)

This SOT-SIM4-ENGINE is **aligned and locked** when:

* Folder structure matches §1 (modulo minor naming refinements), and especially:
  * runtime tick pipeline lives in `runtime/tick.py` + `runtime/scheduler.py`
  * snapshots/diffs/episodes live in `snapshot/*`
  * narrative is contract-first in `narrative/interface.py`
  * integration exports stable artifacts via `integration/*`
* All modules respect:
  * **SOP-100** DAG & mutation rules
  * **SOP-200** tick + determinism rules
  * **SOP-300** substrate/semantic split and 7-layer mapping
* ECS components correspond to Free Agent Spec substrates.
* ECS systems implement the pipelines defined in SOP-300 (§7) and are ordered by `ecs/systems/scheduler_order.py`.
* Narrative influence is only via Phase A integration and `NarrativeState`/contract DTOs, never direct kernel mutation.
* Export artifacts remain deterministic and replayable (validated by existing test suites in `backend/sim4/*/tests`).

## Appendix A: initial engine spec (pre-implementation)

> `NOTE:` **THIS IS NOT THE REFLECTION OF CURRENT IMPLEMENTATION.** The current implementation is described in the main sections of this document.

This is provided as extra context and to identify any gaps vs the original plan.

```text
sim4/
   ├── runtime/                  # tick, engine, scheduler, diff, replay
   │   ├── engine.py             # SimulationEngine (deterministic orchestrator)
   │   ├── clock.py              # TickClock, DeltaTime
   │   ├── scheduler.py          # PhaseScheduler (SOP-200 phases)
   │   ├── diff.py               # State diff builder (ECS + world)
   │   ├── history.py            # HistoryBuffer, event logs
   │   ├── replay.py             # ReplayEngine
   │   ├── events.py             # GlobalEvent, LocalEvent, EventBus
   │   ├── world_context.py      # WorldContext: runtime façade owning world subsystems (does not own ECS)
   │   └── episode.py            # Episode metadata hooks (for narrative arc)
   │
   ├── ecs/                      # ECS core (Rust-portable deterministic substrate)
   │   ├── world.py              # ECSWorld — SOA storage, entity registry
   │   ├── entity.py             # EntityID, allocation, tagging helpers
   │   ├── storage.py            # SOA / archetype-like storage backend
   │   ├── archetype.py          # Archetype definitions & layout rules
   │   ├── query.py              # ECS query engine (read/write views)
   │   ├── components/           # Agent + world-substrate components
   │   │   ├── __init__.py
   │   │   ├── identity.py       # AgentIdentity, ProfileTraits, SelfModelSubstrate
   │   │   ├── embodiment.py     # Transform, Velocity, RoomPresence, PathState
   │   │   ├── perception.py     # PerceptionSubstrate: visibility, salience, attention
   │   │   ├── belief.py         # BeliefGraphSubstrate, AgentInferenceState, SocialBeliefWeights
   │   │   ├── drives.py         # DriveState (curiosity, safety, attachment, etc.)
   │   │   ├── emotion.py        # EmotionFields (tension, mood drift, affective charge)
   │   │   ├── social.py         # SocialSubstrate: relationship weights, trust, factions
   │   │   ├── motive_plan.py    # MotiveSubstrate, PlanLayerSubstrate (plan steps, confidence)
   │   │   ├── intent_action.py  # PrimitiveIntent, SanitizedIntent, ActionState,
   │   │   │                     # MovementIntent, InteractionIntent
   │   │   ├── narrative_state.py# NarrativeState (LLM-owned, semantic refs only)
   │   │   ├── inventory.py      # InventorySubstrate, item refs (IDs only)
   │   │   └── meta.py           # Debug flags, SystemMarkers, Tags
   │   └── systems/              # Deterministic systems (SOP-300 §7)
   │       ├── __init__.py
   │       ├── perception_system.py           # PerceptionSystem
   │       ├── cognitive_preprocessor.py      # CognitivePreprocessor
   │       ├── emotion_gradient_system.py     # EmotionGradientSystem
   │       ├── drive_update_system.py         # DriveUpdateSystem
   │       ├── motive_formation_system.py     # MotiveFormationSystem
   │       ├── plan_resolution_system.py      # PlanResolutionSystem
   │       ├── intent_resolver_system.py      # IntentResolverSystem
   │       ├── movement_resolution_system.py  # MovementResolutionSystem
   │       ├── interaction_resolution_system.py# InteractionResolutionSystem
   │       ├── social_update_system.py        # SocialUpdateSystem
   │       ├── action_execution_system.py     # ActionExecutionSystem
   │       ├── inventory_system.py            # InventorySystem (optional substrate)
   │       └── scheduler_order.py             # Explicit mapping: systems → SOP-200 phases
   │
   ├── world/                    # Environment: rooms, layout, assets, nav
   │   ├── identity/             # Static identity layer
   │   │   ├── world_identity.py # WorldIdentity
   │   │   ├── room_identity.py  # RoomIdentity
   │   │   ├── asset_identity.py # AssetIdentity
   │   │   └── npc_identity.py   # Optional prefab templates
   │   ├── graph/                # Navigation graph (read-only to ECS via runtime)
   │   │   ├── navgraph.py
   │   │   ├── links.py
   │   │   └── spatial_index.py
   │   ├── layout/               # Room layout, tilemaps, collision
   │   │   ├── layout_spec.py
   │   │   └── collision_map.py
   │   ├── rooms/                # Runtime room state (occupants, doors, props)
   │   │   ├── room_state.py
   │   │   └── room_manager.py
   │   ├── assets/               # Runtime asset state
   │   │   ├── asset_state.py
   │   │   └── asset_manager.py
   │   ├── events.py             # World-level events (weather, crowd, factory shifts)
   │   ├── adapters.py           # WorldViews (vis/occlusion, nav views) for runtime → ECS
   │   └── world_state.py        # Root world model (no ECS imports)
   │
   ├── narrative/                # LLM-powered semantic mind (sidecar)
   │   ├── generator.py          # LLM narrative + dialog + inner-monologue generator
   │   ├── pipeline.py           # Multi-agent narrative pipeline (batch, scheduling)
   │   ├── memory.py             # Long-term narrative memory (semantic compression/recall)
   │   ├── reflection.py         # ReflectionLayer semantic logic (L6)
   │   ├── goals.py              # High-level goal formation + GoalSuggestions
   │   ├── filters.py            # Safety / alignment filters for narrative outputs
   │   └── adapters.py           # Kernel-facing types: IntentSuggestions, GoalSuggestions,
   │                             # mapping snapshots → prompts / back
   │
   ├── snapshot/                 # Deterministic view for Godot / clients
   │   ├── builder.py            # WorldSnapshotBuilder (ECS + world + narrative)
   │   ├── schema.py             # Snapshot data schemas (WorldSnapshot, AgentSnapshot)
   │   ├── serializer.py         # JSON-safe serializer
   │   └── diff_adapter.py       # SnapshotDiff builder for streaming
   │
   ├── integration/              # External integration layers (IO only)
   │   ├── godot_ws_server.py    # WebSocket server for Godot live viewer
   │   ├── api.py                # REST/HTTP endpoints (optional)
   │   └── config/
   │       └── defaults.yaml     # Engine configuration templates
   │
   └── util/
   ├── random.py             # Deterministic RNG helpers (SOP-200)
   ├── logging.py            # Structured logging
   └── profiler.py           # Tick-by-tick profiling, debug hooks
```