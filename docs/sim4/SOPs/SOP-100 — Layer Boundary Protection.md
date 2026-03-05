# 🧱 SOP-100 — Layer Boundary Protection
_**The Layer Purity Contract for Sim4–SimX**_
_(Draft 1.0 — Architect-Level, Rust-Aligned, Long-Horizon Safe)_

---

## Purpose
To guarantee that the Sim4 engine remains structurally stable, Rust-portable, and capable of scaling into **SimX (emergent narrative city)** by enforcing **strict**, **inviolable boundaries** between the _**six engine layers**_:
```text
runtime/
ecs/
world/
narrative/
snapshot/
integration/
```

SOP-100 ensures:
* no layer leaks
* no circular dependencies
* no simulation ↔ narrative contamination
* no backend logic in frontend layers
* full determinism preservation
* Rust-clean architecture

This is the **most important structural SOP** after SOP-000.

> **Kernel vs Sidecar**
> **Kernel** = `runtime` + `ecs` + `world` (deterministic simulation core)  
> **Sidecar** = `narrative` (nondeterministic meaning-making)  
> `snapshot` + `integration` = pure **IO** / **view**, never mutating kernel.

---

## 1. The Six-Layer DAG (Directed Acyclic Graph)
All dependencies must follow this exact DAG:
```text
Kernel:   runtime → ecs → world
                \         \
                 \         → snapshot → integration
                  \
                   → (read-only views) → narrative
narrative → (suggestion queues) → runtime (Phase A integration ONLY)
```

### ✔ Valid arrows
* `runtime → ecs`
* `ecs → world`
* `world → snapshot`
* `runtime → world` (can call world subsystems, but must not mutate world state directly - only via ECS)
* `snapshot → integration`
* `narrative → world` (only via adapters – read-only except NarrativeState writes)
* `narrative → ecs` (via read-only snapshots and outbound suggestion queues (IntentSuggestions, GoalSuggestions, etc.) except NarrativeState writes)

### ❌ Invalid arrows (forbidden by contract)
* `ecs → runtime`
* `world → ecs` (world cannot import or call ECS)
* `narrative → runtime` (no direct control over tick)
* `runtime → narrative` (narrative does not interfere with kernel state, runtime can call narrative only via queues/interfaces)
* `snapshot → world`
* `integration → snapshot/ecs/world/runtime`
* `world → narrative` (world CANNOT invoke or depend on LLM modules)

This must remain **a DAG** for Rust-compatibility and architectural sanity.

---

## 2. Allowed vs Forbidden Behavior Per Layer
Below is the explicit behavior matrix.

---

### 2.1. `runtime/`
#### Allowed:
* own the tick
* call ECS systems in deterministic order
* call `world/` subsystems
* pass read-only world views into ECS systems
* aggregate and forward sanitized narrative suggestions into Phase A (see SOP-200)
* produce history/event logs
* trigger snapshot builder

#### Forbidden:
* storing ECS component data
* calling narrative logic directly (only via queues/interfaces)
* mutating world state directly (must go through ECS or world subsystems)
* containing agent cognition logic
* performing I/O operations

Runtime **orchestrates** — it never “knows” semantics.

---

### 2.2. `ecs/`
#### Allowed:
* define components
* store component values (pure SOA)
* run deterministic systems
* manage entity lifecycles
* provide queries over ECS state
* consume **read-only world views** and sanitized narrative suggestions **passed in as data** from `runtime/`

#### Forbidden:
* referencing world geometry, rooms, assets, or navigation directly
* importing world/ modules directly (no from world... in ECS code)
* importing narrative/ or calling narrative APIs
* importing runtime modules
* performing I/O or random OS calls
* allocating arbitrary new component types at runtime
* implementing “meaning-making” or LLM logic
* interpreting natural language

ECS is the **physics of agent behavior and cognitive substrate** — not their minds and not the environment implementation.

---

### 2.3. `world/`
#### Allowed:
* define room identities
* maintain room state
* maintain asset state
* manage world graph
* provide spatial queries (visibility, reachability)
* receive ECS-driven movement and interaction commands (world update requests)
* schedule deterministic world events

#### Forbidden:
* performing LLM computations
* storing narrative output in world state (no semantic logs here)
* mutating ECS component values directly
* calling ECS systems
* importing `ecs/` or `narrative/`

World is **the environment**, not the brain.

---

### 2.4. `narrative/`
#### Allowed:
* read **snapshots** of ECS state (substrate only)
* read world state through **read-only adapters/views**
* update NarrativeState, BeliefState, GoalState
* maintain its own semantic state:
  * `NarrativeState`
  * semantic `BeliefState`
  * semantic `GoalState`
  * memory indices, reflection logs, prompt caches, etc.
* generate dialog, thought, reflection, inner monologue
* generate **semantic** beliefs, goals, and interpretations
* propose new **IntentSuggestions** and **GoalSuggestions** via adapters/queues
* run **asynchronously**, outside deterministic tick (**Phase I** in SOP-200)

#### Forbidden:
* modifying any **kernel ECS component** (including Transform, Intent, Action, SocialState, EmotionalState, Motive, Plan, Movement/Interaction intents)
* writing directly to `world/` state
* calling `runtime/` or controlling tick order
* importing `runtime/`, `ecs/`, or `world/` directly (only through stable API/adapters)
* injecting nondeterminism into ECS or world (only narrative-local state is allowed to be nondeterministic)

Narrative is a **meaning-making sidecar**, not part of the deterministic simulation kernel.

---

### 2.5. `snapshot/`
#### Allowed:
* read world and ECS
* read narrative state (via stable interfaces)
* build a deterministic snapshot
* serialize snapshot representations for viewers

#### Forbidden:
* mutating ECS, world, or narrative state
* invoking systems
* performing I/O (except serialization via `integration/`)
* storing persistent data

Snapshots are **pure views** (read-only), always.

---

### 2.6. `integration/`
#### Allowed:
* send snapshots to Godot or other frontends
* expose HTTP/WebSocket API
* serve configuration
* translate engine outputs for external tools

#### Forbidden:
* mutating any simulation data (kernel or narrative)
* running systems
* invoking narrative generation
* reading/writing ECS or world directly (must go via `snapshot/` outputs)
* influencing tick order or pace

Integration is **purely an IO layer**, not simulation-critical.

---

## 3. Global Mutation Rules

To guarantee determinism and clean separation:

### 3.1. Kernel Mutation Rules

Only these layers may mutate **kernel state**:
* `ecs/` — via deterministic systems during the allowed tick phases (see SOP-200)
* `world/` — via deterministic `WorldContext` subsystems, applying ECS-issued commands

No other layer may mutate kernel state (ECS components + world data).

`runtime/`, `snapshot/`, `integration/`, and `narrative/` must treat kernel state as read-only.

### 3.2. Narrative Mutation Rules

Narrative is allowed to mutate **only its own internal state**:
* narrative-local `NarrativeState`
* semantic `BeliefState` and `GoalState` (living in the narrative engine, not ECS)
* reflection logs, memory banks, prompt caches
* outbound suggestion queues (IntentSuggestions, GoalSuggestions, etc.)

Narrative has **zero direct write access** to kernel ECS/world state.

### 3.3. View Layers
* `snapshot/` and `integration/` must be 100% mutation-free with respect to both **kernel** and **narrative** state.

### ✔ Only these layers may perform mutations:
* **ecs/** — via systems
* **world/** — via WorldContext subsystems
* **narrative/** — ONLY NarrativeState, BeliefState, GoalState

### ❌ No other layer may mutate anything.
### ❌ snapshot/ and integration/ must be 100% mutation-free.

---

## 4. Determinism Boundaries
To maintain Rust-portability and SimX replayability:
* ECS systems must be pure functions of (ECS state + world views + dt + seeded RNG).
* `world/` subsystems must be deterministic functions of (world state + ECS commands + seeded RNG).
* `runtime/` may not introduce randomness except via the approved RNG module.
* narrative nondeterminism is quarantined to narrative-local state and suggestion queues;
  * the **kernel only ever sees sanitized, deterministically integrated suggestions** (**Phase A** in SOP-200).

If nondeterminism enters the kernel (ECS + world), it is a **catastrophic violation** of SOP-100.

---

## 5. World–ECS Interaction Protocol
The only legal interactions:

### ✔ ECS → world
* agent movement updates → world updates room occupancy, spatial placement
* interaction/world commands → world changes asset/room state deterministically
* perception → ECS systems consume read-only world views supplied by runtime/world, world is queried for geometry and supplies obstacles and graphs

### ❌ world → ecs
* `world/` cannot directly mutate ECS components or call ECS systems.
* `WorldContext` may **emit world events or data** that runtime passes into ECS as **inputs**, but all ECS mutations must be performed by ECS systems.
WorldContext may **request** changes, but ECS systems must apply them.

This ensures future Rust ECS purity and clear separation of environment vs agent substrate.

---

## 6. Narrative Isolation Protocol
(Overlaps with SOP-400 but defined here structurally)

Narrative:
* runs after the tick (post **Phase H**, as **Phase I** in SOP-200)
* sees deterministic kernel state via snapshots/adapters
* writes only to narrative-local components (semantic beliefs/goals, NarrativeState, memory)
* never writes action/intent or other kernel components directly
* must use adapters to propose changes via suggestion queues (IntentSuggestions, GoalSuggestions, belief hints)

Adapters then:
* sanitize proposals
* ensure validity and consistency
* map semantic content into substrate-safe commands
* ensure deterministic ordering and integration (**Phase A** of next tick)
* enforce limits to avoid injection or abuse

This ensures the simulation stays **physics-like** and narrative content stays **meaning-like**.

---

## 7. Snapshot Read-Only Contract
Snapshot must:
* never mutate ECS, world, or narrative state
* never call world update methods
* never call ECS mutation functions
* never call narrative generation
* never store persistent data

Snapshot builders are **pure views** (observational pipelines).

---

## 8. Integration Read-Only Contract

Integration may:
* serialize
* transmit
* log

Integration may NOT:
* mutate world, ECS, or narrative
* run systems
* adjust tick
* hold references that can mutate engine state

Integration is an **observer**.

---

## 9. Enforcement Rules (Strict)
Architect-GPT must refuse any action that:
* crosses layer boundaries (imports or calls)
* violates DAG
* introduces circular imports
* lets narrative directly mutate ECS/world
* places simulation logic in the narrative layer
* places world logic into ECS systems or vice versa
* allows snapshot or integration to mutate engine state
* routes randomness into kernel outside the central RNG
* uses narrative to bypass the ECS → world command pipeline

If Stepan requests a change that would violate boundaries, Architect-GPT must:
1. Pause
2. Flag violation
3. Offer compliant alternatives

Never proceed with a boundary breach.

---

## 10. Completion Conditions

SOP-100 is satisfied only when:
* all code respects the DAG and layer responsibilities
* imports follow the DAG (no back-edges)
* each layer has clear, enforced responsibilities
* world is decoupled from ECS (no direct writes from world to ECS)
* narrative is isolated from kernel simulation (read-only + suggestions only)
* snapshot remains pure view logic
* integration remains pure IO
* **determinism boundaries** (SOP-200) and **substrate/semantic split** (SOP-300) are not violated

Once these hold, SOP-100 is locked for that iteration.