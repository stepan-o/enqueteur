# 🌐 SIM4 — FINAL FOLDER STRUCTURE (v1.0)
_**Python prototype, Rust-aligned, fully scalable**_

Designed in accordance with SIMX vision.
```text
sim4/
├── runtime/                  # time, engine, scheduler, diff, replay
│   ├── engine.py            # SimulationEngine (deterministic orchestrator)
│   ├── clock.py             # TickClock, DeltaTime
│   ├── scheduler.py         # PhaseScheduler (ordered ECS phases)
│   ├── diff.py              # State diff for snapshots
│   ├── history.py           # HistoryBuffer, event logs
│   ├── replay.py            # ReplayEngine
│   ├── events.py            # GlobalEvent, LocalEvent, EventBus
│   └── episode.py           # Episode metadata (for narrative arc)
│
├── ecs/                      # ECS core (Rust-portable)
│   ├── world.py             # ECSWorld — pure data container
│   ├── entity.py            # EntityID, tagging, identity utilities
│   ├── storage.py           # SOA storage (archetype-like)
│   ├── archetype.py         # Archetype definitions (lightweight)
│   ├── query.py             # ECS query engine
│   ├── components/          # All component types
│   │   ├── __init__.py
│   │   ├── identity.py      # Name, Role, ProfileTraits
│   │   ├── transform.py     # Transform (x,y), Vel, RoomID
│   │   ├── perception.py    # Perception, VisualProps
│   │   ├── cognition.py     # CognitiveState, MemoryTraces
│   │   ├── emotion.py       # EmotionalState
│   │   ├── social.py        # SocialState, relationships
│   │   ├── intent.py        # IntentState, MovementIntent, ActionState
│   │   ├── narrative.py     # NarrativeState (LLM sidecar)
│   │   ├── inventory.py     # Items, assets
│   │   └── meta.py          # Tags, debug flags, system markers
│   └── systems/             # All deterministic systems
│       ├── __init__.py
│       ├── perception_system.py
│       ├── cognition_system.py
│       ├── emotion_system.py
│       ├── intention_system.py
│       ├── action_system.py
│       ├── movement_system.py
│       ├── social_system.py
│       ├── inventory_system.py
│       ├── resolution_system.py
│       └── scheduler_order.py  # Explicit phase declarations
│
├── world/                    # Game world: rooms, layout, assets
│   ├── identity/            # Static data
│   │   ├── world_identity.py
│   │   ├── room_identity.py
│   │   ├── asset_identity.py
│   │   └── npc_identity.py  # Optional prefab identities
│   ├── graph/               # Navigation graph
│   │   ├── navgraph.py
│   │   ├── links.py
│   │   └── spatial_index.py
│   ├── layout/              # Room layout, tilemaps, obstacles
│   │   ├── layout_spec.py
│   │   └── collision_map.py
│   ├── rooms/               # Runtime room state
│   │   ├── room_state.py
│   │   └── room_manager.py
│   ├── assets/              # Items, props, interactive objects
│   │   ├── asset_state.py
│   │   └── asset_manager.py
│   ├── events.py            # World-level events (weather, crowd)
│   └── world_context.py     # WorldContext: owns ECSWorld + world subsystems
│
├── narrative/                # LLM-powered cognitive layer
│   ├── generator.py         # LLM narrative + dialog generator
│   ├── pipeline.py          # Multi-agent narrative pipeline (batch eligible)
│   ├── memory.py            # Long-term memory compression + recall
│   ├── reflection.py        # Belief revision, self-model, metacognition
│   ├── goals.py             # High-level goal formulation
│   ├── filters.py           # Alignment & safety filters (sanity)
│   └── adapters.py          # Interface bridging ECS <-> LLM
│
├── snapshot/                 # Deterministic view for Godot
│   ├── builder.py           # WorldSnapshotBuilder
│   ├── schema.py            # Data schemas for snapshots
│   ├── serializer.py        # JSON-safe serializer
│   └── diff_adapter.py      # SnapshotDiff for streaming
│
├── integration/              # External integration layers
│   ├── godot_ws_server.py   # WebSocket server for Godot live viewer
│   ├── api.py               # REST/HTTP endpoints (optional)
│   └── config/              # Engine configuration templates
│       └── defaults.yaml
│
└── util/
├── random.py            # Deterministic RNG helpers
├── logging.py           # Structured logging
└── profiler.py          # Tick-by-tick profiling
```

## SOPs and SOTs

### 🧩 Relationship Between SOPs and SOTs
**SOPs = Operating Procedures**

How architects behave. How cycles work.  
They control _process_ and _governance_.

**SOTs = Source of Truth**

What the engine is.  
They control _architecture & system definition_.

### SOT = Source of Truth
SOT — system overview & technical spec, a canonical document that defines one stable piece of the system.

**Purpose:**
* a permanent, architecture-level document
* the single authoritative definition for a subsystem or domain
* something all future architects must obey
* non-temporary and non-negotiable unless explicitly revised
* a living but stable canonical source of system truth
* the basis against which code is validated
* the “bible page” for a domain

**What in includes:**
* define architecture
* describe modules
* define APIs and boundaries
* outline long-arc strategy (Sim4 → SimX)
* guide implementation design
* not prescriptive about processes
* does not enforce rules

**Audience:**
* architects
* senior engineers
* future Rust migration team
* Godot frontend devs

**✔ Output examples:**
* Directory structure
* Layer responsibilities
* Data flow diagrams
* Component definitions
* Class responsibilities
* Simulation rules
* ECS design
* World model

This is the “Roman blueprint”.

---

### SOP — Standard Operating Procedure
Purpose:
* enforce rules
* govern behavior of contributors and subsystems
* restrict what code can and cannot do
* define the process and boundaries
* mandatory for bots like Junie

Audience:
* Junie
* AI dev agents
* any contributor
* CI/QA

### ✔ Output examples:
* “ECS MUST NOT call world/graph”
* “Snapshot MUST NOT mutate state”
* “Narrative MAY ONLY modify NarrativeState”
* “Integration MAY ONLY publish snapshots”
* “Systems MUST be pure functions”

This is the “constitution”.

# ✅ Sim4 Engine SOP Library (5 Documents Total)

Every sim architect (LLM or human) should be required to read them before touching code.

These 5 SOPs cover everything the system actually needs.

---

## 📗 SOP-000 — Architect Operating Contract (AOC)
_(meta-SOP, the contract between Stepan and Architect-GPT)_

**Purpose:**  
Define how Architect-GPT behaves as an architect.

Covers:
* obedience to long-arc plan
* anti-drift protocol
* memory of locked structure
* iterative waterfall discipline
* “no premature coding” rule
* how to request clarifications
* when to refuse changes
* when to propose architecture evolutions
* how sub-sprints function
* how SOTs connect to implementable code

The architect should acknowledge:
* it is not a coding assistant
* it is not a chatty helper
* it is not a general-purpose LLM
* it is a long-horizon system architect

**Required for all future LLMs architects**

---

## 📗 SOP-100 — Layer Boundary Protection
**Purpose:**  
Ensure nothing violates the six-layer DAG:
* runtime
* ecs
* world
* narrative
* snapshot
* integration

**Covers:**
* allowed vs forbidden dependencies
* mutation rules
* determinism boundaries
* narrative isolation
* world–ECS adapters
* snapshot read-only rules
* integration read-only rules

This is the **constitution** of the entire engine.

If this SOP holds, architecture won't collapse.

---

## 📗 SOP-200 — Determinism & Simulation Contract

**Purpose:**  
Guarantee reproducibility and Rust portability.

**Covers:**
* deterministic randomness (runtime RNG)
* no external calls in sim-critical path
* no I/O in systems
* order stability rules
* ECS system purity requirements
* world updates ordering rules
* how tick progression works
* snapshot sampling protocol

Basically:  
No nondeterminism leaks into the core.

---

## 📗 SOP-300 — Component & System Lifecycle Rules

**Purpose:**  
Ensure ECS is stable, predictable, and upgradable.

**Covers:**
* rules for adding new components
* rules for modifying existing ones
* IDL-like standard structure for components
* system lifecycle and update-order rules
* how to create new systems following phase order
* how to test system consistency
* how to document interactions in SOT

This prevents:
* “too many components”
* “systems becoming spaghetti logic”
* “psych cognition layer hacks”
* “reenacting Skyrim AI chaos”

---

## 📗 SOP-400 — LLM Narrative Isolation

**Purpose:**  
Ensure emergent story generation never infects the deterministic sim core.

**Covers:**
* narrative NEVER influences physics/action/intent
* narrative writes only to NarrativeState
* narrative triggered after tick
* narrative has no system code
* narrative is sandboxed by world & ecs
* narrative batching rules
* narrative cache rules
* reflection frequency

This allows you to have Disco Elysium vibes without ever breaking the simulation core.

---

## 📘 Summary — 5 SOPs Total
| SOP                                  | 	Purpose                            | 	Without it, what breaks?       |
|--------------------------------------|-------------------------------------|---------------------------------|
| SOP-000 Architect Operating Contract | 	Controls behavior of Architect-GPT | 	Architecture drift, bad cycles |
| SOP-100 Layer Boundaries             | 	Protects structure                 | 	Sim collapses, Rust port fails |
| SOP-200 Determinism Contract         | 	Reproducible sim                   | 	Emergence becomes noise        |
| SOP-300 ECS Lifecycle Rules          | 	Stable agent model                 | 	Spaghetti AI, unmaintainable   |
| SOP-400 Narrative Isolation          | 	Integrates LLM safely              | 	Random chaos overwrites sim    |

This is all you need.

And frankly — this is all any solo architect + LLM partner needs to build Sim4 through SimX.

More SOPs add friction without adding benefit.

## Future us—14 SOP Library that we'll have one day

```text
CATEGORY A — FOUNDATION
SOP-001 — Development Core Protocol
SOP-002 — Architectural Layer Boundaries
SOP-003 — Rust Migration Contract

CATEGORY B — ECS
SOP-100 — ECSWorld State Model
SOP-101 — Component Specification & Rules
SOP-102 — System Design Rules
SOP-103 — Querying & Archetypes
SOP-104 — ECS Debugging & Verification

CATEGORY C — WORLD ENGINE
SOP-200 — WorldContext Specification
SOP-201 — World Identity & Layout
SOP-202 — World Event Model

CATEGORY D — NARRATIVE LAYER
SOP-300 — Narrative State & LLM Integration
SOP-301 — Multi-Agent Narrative Orchestration

CATEGORY E — SNAPSHOT + INTEGRATION
SOP-400 — Snapshot Specification & Godot API Contract

CATEGORY F — RUNTIME ENGINE
SOP-500 — Simulation Loop, Scheduler & Tick Semantics

CATEGORY G — LONG-ARC VISION
SOP-900 — Evolvability & Emergent Narrative Roadmap
```

**Why 14?** :sweat_smile:      
Because each major subsystem is independent (per our architecture),
each has clear boundaries,  
and each **must be explicitly controlled to avoid drift**.

This set is _minimal but complete_ for the entire Sim4→SimX arc
and gives a clean path to Rust.

---

## 🔵 CATEGORY A — FOUNDATION (3 SOPs)
These define the high-level rules for the entire engine.

---

### SOP-001 — Development Core Protocol
**Purpose:** governance, determinism, Rust-portability rules, Junie constraints.

### SOP-002 — Sim4 Architectural Layer Boundaries
Defines the **exact responsibilities** and **forbidden cross-layer interactions** for:
* ECS
* World
* Runtime
* Narrative
* Snapshot
* Integration

This prevents the most common drift: systems reaching into the world; snapshots mutating ECS; narrative touching simulation, etc.

---

### SOP-003 — Rust Migration Contract
Defines from day one:
* allowed Python language features
* prohibited dynamic patterns
* memory model assumptions
* determinism equivalence rules
* exact migration path for ECSWorld → Rust ECS
* required invariants for systems

This ensures everything we build right now compiles mentally to Rust later.

---

## 🟩 CATEGORY B — ECS (5 SOPs)

The ECS subsystem is the foundation of everything.  
These must be extremely precise.

---

### SOP-100 — ECSWorld State Model
Defines:
* what ECSWorld is
* how entity storage works
* how all component data lives
* invariants for mutation
* how queries are resolved

This is the backbone.

---

### SOP-101 — Component Specification & Rules
Defines:
* component naming rules
* category families (Identity, Spatial, Perception, Cognition, Emotion…)
* serialization constraints
* update constraints
* Rust-compatible dataclass disciplines

Also explicitly defines:  
**No component ever contains references to objects outside ECS.**

---

### SOP-102 — System Design Rules
Defines:
* phases
* system naming and ordering
* what systems may modify
* system-level determinism rules
* timing rules (dt constraints)
* input/output constraints

Also defines the Sim4 → SimX psych layers integration point.

---

### SOP-103 — Querying and Archetypes
Defines:
* archetype formation
* rules for entity insertion/removal
* how query signatures are validated
* O(1) performance constraints
* allowed access patterns

---

### SOP-104 — ECS Debugging & Verification

Defines:
* invariant checks
* determinism replay
* archetype consistency tests
* “state poison” detector
* component-level leak detection

---

## 🟦 CATEGORY C — WORLD ENGINE (3 SOPs)
The world is a separate domain from ECS.

---

### SOP-200 — WorldContext Specification
Defines:
* the role of WorldContext
* its runtime loop
* its separation from ECS
* room/asset/world-graph ownership
* world-level events
* room transitions
* asset inventory state

This ensures we keep the city/world simulation modular.

---

### SOP-201 — World Identity & Layout
Defines:
* RoomIdentity
* WorldIdentity
* Graph definitions
* Prefabs
* Layout loading flow
* Asset identity vs runtime state

---

### SOP-202 — World Event Model
Defines:
* event types
* event propagation
* world-level logs
* how events are captured for narrative / history buffer

---

## 🟨 CATEGORY D — NARRATIVE LAYER (2 SOPs)
Narrative is optional in Sim4 but REQUIRED by SimX.

---

### SOP-300 — Narrative State & LLM Integration
Defines:
* narrative components
* reflection components
* sidecar architecture
* how narrative generator plugs into runtime
* how agent identity flows into prompts
* how to keep narrative deterministic (seeded and queued)

---

### SOP-301 — Multi-Agent Narrative Orchestration
Defines:
* reflection pipelines
* synchronous vs asynchronous LLM calls
* narrative throttling (tokens per tick)
* caching rules
* how narrative interacts with snapshots

---

## 🟥 CATEGORY E — SNAPSHOT + INTEGRATION (1 SOP)

### SOP-400 — Snapshot Specification & Godot API Contract
Defines:
* world snapshot structure
* entity snapshot structure
* narrative snapshot structure
* diff format
* encoding rules
* integration server contract
* Godot message protocol

This prevents incoming architectural drift from UI demands.

---

## 🟧 CATEGORY F — RUNTIME ENGINE (SCHEDULER) (1 SOP)

### SOP-500 — Simulation Loop, Scheduler & Tick Semantics
Defines:
* tick ordering
* dt rules
* when ECS runs
* when world systems run
* when narrative runs
* snapshot timing
* replay rules
* rollback constraints

This is the “heart” of the engine.

---

## 🟪 CATEGORY G — LONG-ARC VISION (Sim4 → SimX) (1 SOP)

### SOP-900 — Evolvability & Emergent Narrative Roadmap

Defines the future architecture requirements:
* emergent Disco Elysium
* multi-agent internal minds
* reflective inner monologue
* memory networks
* long-term social/identity arcs
* district-level simulation
* scaling patterns
* Rust transition
* distributed simulation

This prevents short-term development from painting us into a corner.