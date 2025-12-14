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
* holds **substrates** for the 7-layer agent mind (L1–L5, plus L7 numeric vectors)
**2. Narrative Mind Engine (Sidecar)**
* `narrative/`
* nondeterministic LLM meaning-making
* reads snapshots / views of kernel state
* produces semantic narrative state + intent/goal suggestions, which are materialized as ECS substrate components (e.g. `PrimitiveIntent`, updates to `NarrativeState`) via a runtime bridge and sanitized before the next tick 
3. Presentation & IO Layers
* `snapshot/`, `integration/`
* read-only views, Godot/Web APIs, no simulation logic

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

## 1. Final Folder Structure (v1.0)
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

Key structural changes vs old v0.1:
* `world_context.py` moved to `runtime/`, so:
  * `runtime` orchestrates ECS + world in line with SOP-100.
  * `world/` no longer owns `ECSWorld` directly (keeps layer purity).
* ECS components and systems renamed / structured to match **Free Agent Spec** + SOP-300 (**substrate layers**, **movement/interaction pipeline**).
* Removed old “cognition/emotion/intent” generic names in favor of **Belief/Drives/EmotionFields/MotivePlan/IntentAction** etc.

---

## 2. Mapping to the 7-Layer Agent Mind
From SOP-300 + Free Agent Spec, the agent mind layers:
```text
L1 — Embodied & Raw Perception Layer
L2 — Perception & Attention Layer
L3 — Belief, Concept & Self-Model Layer
L4 — Drives & Emotion Fields Layer
L5 — Motives & Planning Layer
L6 — Reflection Layer
L7 — Narrative & Persona/Aesthetic Mind
```

### 2.1 Substrate Components in ECS
#### L1 — Embodied & Raw Perception
* `embodiment.py`
  * `Transform` (x,y / room)
  * `Velocity`
  * `RoomPresence`
  * `PathState`
* `perception.py`
  * raw sensory lists (visible agents, objects)
  * basic attention hooks (which slot is focused)

#### L2 — Perception & Attention
* `perception.py`
  * salience scores
  * attention slots
  * perceptual flags

#### L3 — Belief, Concept & Self-Model
* `identity.py`
  * `SelfModelSubstrate` (identity vector, consistency pressure, drift/contradiction counters)
* `belief.py`
  * `BeliefGraphSubstrate`
  * `AgentInferenceState`
  * `SocialBeliefWeights`

#### L4 — Drives & Emotion Fields
* `drives.py`
  * `DriveState` (`curiosity`, `safety_drive`, `attachment_drive`, etc.)
* `emotion.py`
  * `EmotionFields` (tension, mood drift, affective charge, stress, excitement)

#### L5 — Motives & Planning
* `motive_plan.py`
  * `MotiveSubstrate` (motive activation scores)
  * `PlanLayerSubstrate` (plan steps, plan confidence, revision flags)

#### L6 — Reflection (Semantic Only)
* Lives in `narrative/reflection.py` and related narrative modules.
* No ECS component; only semantic, post-tick.

#### L7 — Narrative & Persona/Aesthetic
* Numeric substrate in ECS:
  * e.g., persona / aesthetic preference vectors stored in `identity.py` or dedicated `persona_substrate` (could be added later as we refine).
* Semantic narrative in `narrative/`:
  * dialog, style, voice, inner monologue.

---

## 3. Tick & Determinism (SOP-200 Alignment)
`runtime/engine.py` implements the canonical tick:
```text
tick(dt):
    1. Lock WorldContext
    2. Update Clock
    3. Phase A: Input Processing & Adapters
    4. Phase B: Perception (ECS systems, read-only world views)
    5. Phase C: Cognition (ECS non-LLM)
    6. Phase D: Intention → ECS Commands (sanitize suggestions)
    7. Phase E: ECS Command Application (mutations in ECS)
    8. Phase F: World Updates (world subsystems)
    9. Phase G: Event Consolidation
    10. Phase H: Diff Recording + History Append
    11. Phase I: Narrative Trigger (post-tick sidecar)
    12. Unlock WorldContext
```

* **Determinism:**
  * All ECS + world mutations happen only in **Phase E/F**.
  * Narrative runs only in **Phase I**, never mutating kernel state directly.
  * RNG usage is centralized in `util/random.py` with seed from scenario.
  * Iteration order is stable (EntityID ascending, registered system order).

`runtime/scheduler.py` and `ecs/systems/scheduler_order.py` define:
* Which system runs in which SOP-200 phase.
* System order within phases.

---

## 4. ECS Systems (Concrete Mapping to SOP-300)
Systems in `ecs/systems/`:
1. **PerceptionSystem** (`perception_system.py`)
* Phase B
* Reads: `Transform`, `RoomPresence`, world geometry via `world/adapters.WorldViews`
* Writes: `PerceptionSubstrate` (visibility, salience, attention slots)
2. **CognitivePreprocessor** (`cognitive_preprocessor.py`)
* Phase C
* Reads: events, BeliefGraphSubstrate
* Writes: updated belief confidences, decay, propagation
* No natural language, no semantic interpretation.
3. **EmotionGradientSystem** (`emotion_gradient_system.py`)
* Phase C
* Reads: DriveState, EmotionFields, events
* Writes: updated EmotionFields (diffusion, drift)
4. **DriveUpdateSystem** (`drive_update_system.py`)
* Phase C
* Reads: events, EmotionFields
* Writes: DriveState (curiosity, safety, etc.)
5. **MotiveFormationSystem** (`motive_formation_system.py`)
* Phase C
* Reads: DriveState, BeliefGraphSubstrate, SocialSubstrate
* Writes: MotiveSubstrate (numeric motive activation)
6. **PlanResolutionSystem** (`plan_resolution_system.py`)
* Phase C
* Reads: MotiveSubstrate, PlanLayerSubstrate
* Writes: PlanLayerSubstrate (plan steps, revision flags)
7. **IntentResolverSystem** (`intent_resolver_system.py`)
* Phase D
* Reads: `PrimitiveIntent` (from adapters & last narrative suggestions), PlanLayerSubstrate, DriveState
* Writes: `SanitizedIntent` (physics-safe, permission-safe)
8. **MovementResolutionSystem** (`movement_resolution_system.py`)
* Phase D
* Reads: `SanitizedIntent`, `Transform`, `RoomPresence`, world nav views
* Writes: `MovementIntent`, `PathState`, `ActionState` (movement modes or `Stuck/Waiting`)
9. **InteractionResolutionSystem** (`interaction_resolution_system.py`)
* Phase D
* Reads: `SanitizedIntent`, target info via world views
* Writes: `InteractionIntent`, `ActionState` and **world update commands** (but not world state directly)
10. **SocialUpdateSystem** (`social_update_system.py`)
* Phase C
* Reads: SocialSubstrate, interaction outcomes
* Writes: updated relationship weights, trust vectors, tension
11. **ActionExecutionSystem** (action_execution_system.py)
* Phase E
* Reads: `MovementIntent`, `InteractionIntent`, `ActionState`
* Writes:
  * ECS-side: `Transform`, `RoomPresence`, `PathState`, interaction memory counters
  * Emits **world commands** to `runtime/world_context.py` for Phase F
  (e.g. `OpenDoor(door_id)`, `MoveItem(item_id, from, to)`)
12. **InventorySystem** (`inventory_system.py`) (optional)
* Phase E
* Handles internal inventory updates after world confirms.

All systems obey:
* No imports of `world/` **directly from ECS**.  
World data arrives via adapters/views injected by runtime (SOP-300 “world inputs as read-only views”).

---

## 5. World Layer (SOP-100 & SOP-200)
`world/` is pure environment:
* Owns **room**, **asset**, **graph**, **layout** state.
* Exposes **read-only views** (e.g., NavigationView, VisibilityView) via `world/adapters.py`.
* Mutations happen via **commands** from `runtime/world_context.py`:

Examples of world commands (structured types):
* `MoveAgent(agent_id, from_room, to_room)`
* `OpenDoor(door_id)`
* `ToggleMachine(machine_id, state)`
* `SpawnItem(item_id, room_id)`
* `DespawnItem(item_id)`

These are applied **only in Phase F** (SOP-200).

`world_context.py` (in runtime) owns:
* `WorldState` instance
* applies world commands deterministically
* provides world views to ECS systems via scheduler

---

## 6. Narrative Layer (Sidecar, SOP-100/SOP-300)

`narrative/` is a **post-tick semantic sidecar**:
* Triggered in **Phase I** (SOP-200) by `runtime/engine.py`.
* Reads:
  * stable snapshot via snapshot/builder.py or
  * special read-only views passed from runtime (AgentView, WorldView, BeliefView).
* Writes:
  * narrative-local memory (`memory.py`)
  * semantic reflection, inner monologue, dialog
  * semantic beliefs/goals (outside ECS numeric substrate)
  * `IntentSuggestions` & `GoalSuggestions` via `narrative/adapters.py`

**Narrative may NOT:**
* mutate ECS components directly (except `NarrativeState` fields that are defined as semantic containers).
* mutate world state.
* affect tick timing.

**How it influences agents:**
1. Narrative outputs `IntentSuggestions`, `GoalSuggestions` for next tick.
2. `runtime/engine.py` feeds them into **Phase A** (input processing).
3. Adapters map them into `PrimitiveIntent`, plan hints, or belief hints.
4. ECS systems deterministically gate/sanitize them.

This matches SOP-300 §9 and SOP-000 §9 (Narrative Obedience).

---

## 7. Snapshot & Integration
* `snapshot/`:
  * builds immutable `WorldSnapshot` / `AgentSnapshot` structures
  * includes ECS (substrates), world state, and optionally high-level narrative annotations
  * no mutation; pure views.
* `integration/`:
  * WebSockets / REST for Godot or other tools
  * cannot call ECS systems or world subsystems directly
  * cannot mutate state; purely IO.

This satisfies SOP-100 contracts for snapshot/integration.

---

## 8. SOP & SOT Library (SOPs + Free Agent Spec)
For Sim4, the **canonical governance set** is now:

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

---

## 9. Completion Condition for Sim4 Engine Spec
This SOT-SIM4-ENGINE is considered **aligned and locked** when:
* Folder structure matches this spec (modulo minor naming refinements).
* All new/modified modules respect:
  * **SOP-100** DAG & mutation rules.
  * **SOP-200** tick & RNG contract.
  * **SOP-300** substrate/semantic split and 7-layer mapping.
* ECS components correspond to Free Agent Spec substrates.
* ECS systems implement the pipelines defined in SOP-300 (§7).
* Narrative sidecar operates only via `IntentSuggestions` / `GoalSuggestions` and `NarrativeState`, never mutating kernel directly.