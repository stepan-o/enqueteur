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

---

## 1. The Six-Layer DAG (Directed Acyclic Graph)
All dependencies must follow this exact DAG:
```
runtime   →   ecs   →   world   →   snapshot   →   integration
                 ↑
           narrative (sidecar, no upstream calls)
```

### ✔ Valid arrows
* `runtime → ecs`
* `ecs → world`
* `world → snapshot`
* `snapshot → integration`
* `narrative → world` (only via adapters – read-only except NarrativeState writes)
* `narrative → ecs` (read-only except NarrativeState writes)

### ❌ Invalid arrows (forbidden by contract)
* `ecs → runtime`
* `world → ecs`
* `narrative → runtime`
* `snapshot → world`
* `integration → snapshot/ecs/world/runtime`
* `world → narrative` (world CANNOT invoke or depend on LLM modules)

This must remain **a DAG** for Rust-compatibility.

---

## 2. Allowed vs Forbidden Behavior Per Layer
Below is the explicit behavior matrix.

---

### 2.1. runtime/
#### Allowed:
* own the tick
* call ECS systems in deterministic order
* call WorldContext subsystems
* produce history/event logs
* trigger snapshot builder

#### Forbidden:
* storing ECS component data
* calling narrative logic
* mutating world state directly (must go through ECS or world subsystems)
* containing agent cognition logic
* performing I/O operations

Runtime orchestrates — it never “knows” semantics.

---

### 2.2. ecs/
#### Allowed:
* define components
* store component values (pure SOA)
* run deterministic systems
* manage entity lifecycles
* provide queries

#### Forbidden:
* referencing world geometry, rooms, assets, or navigation directly
* calling narrative modules
* importing runtime modules
* performing I/O or random OS calls
* allocating arbitrary new component types at runtime
* implementing “meaning-making” or LLM logic

ECS is the physics of agent behavior — not their minds.

---

### 2.3. world/
#### Allowed:
* define room identities
* maintain room state
* maintain asset state
* manage world graph
* provide spatial queries (visibility, reachability)
* receive ECS-driven entity movement
* schedule deterministic world events

#### Forbidden:
* performing LLM computations
* storing narrative output in world state
* mutating ECS component values directly
* calling ECS systems
* importing narrative or adapters

World is **the environment**, not the brain.

---

### 2.4. narrative/
#### Allowed:
* read snapshots of ECS state
* read world state through adapters
* update NarrativeState, BeliefState, GoalState
* generate dialog, thought, reflection
* propose new IntentState updates (sanitized by adapters)
* run asynchronously, outside deterministic tick

#### Forbidden:
* modifying any ECS component except NarrativeState
* modifying Transform, Intent, Action, SocialState, EmotionalState
* directly affecting physics or movement
* injecting nondeterminism into ECS
* writing world state
* calling runtime

Narrative is a **meaning-making sidecar**, not part of the simulation kernel.

---

### 2.5. snapshot/
#### Allowed:
* read world and ECS
* read narrative state
* build a deterministic snapshot
* serialize it

#### Forbidden:
* mutating ECS, world, or narrative state
* invoking systems
* performing I/O (except serialization via integration)
* storing persistent data

Snapshots are read-only, always.

---

### 2.6. integration/
#### Allowed:
* send snapshots to Godot
* expose HTTP/WebSocket API
* serve configuration
* translate engine outputs for external tools

#### Forbidden:
* mutating any simulation data
* running systems
* invoking narrative generation
* reading/writing ECS or world
* influencing tick order or pace

Integration is **purely an IO layer**, not simulation-critical.

---

## 3. Global Mutation Rules

To guarantee determinism:

### ✔ Only these layers may perform mutations:
* **ecs/** — via systems
* **world/** — via WorldContext subsystems
* **narrative/** — ONLY NarrativeState, BeliefState, GoalState

### ❌ No other layer may mutate anything.
### ❌ snapshot/ and integration/ must be 100% mutation-free.

---

## 4. Determinism Boundaries
To maintain Rust-portability:
* ECS systems must be pure functions of (world state + dt).
* world subsystems must be deterministic.
* runtime may not introduce randomness except via approved RNG.
* narrative nondeterminism is quarantined to NarrativeState, never ECS.

If nondeterminism enters the simulation kernel, it is a **catastrophic violation** of SOP-100.

---

## 5. World–ECS Interaction Protocol
The only legal interactions:

### ✔ ECS → world
* agent moved → world updates room occupancy
* perception → world is queried for geometry
* movement → world supplies obstacles and graphs

### ❌ world → ecs
World cannot directly mutate ECS components.
WorldContext may **request** changes, but ECS systems must apply them.

This ensures future Rust ECS purity.

---

## 6. Narrative Isolation Protocol
(Overlaps with SOP-400 but defined here structurally)

Narrative:
* runs after tick
* sees deterministic state
* writes only to LLM-owned components
* never affects action/intent directly
* must use adapters to propose changes

Adapters sanitize:
* validity
* determinism
* conflicts
* injection risk

This ensures the simulation stays physics-like and narrative content stays meaning-like.

---

## 7. Snapshot Read-Only Contract
Snapshot must:
* never mutate state
* never call world update methods
* never call ECS mutation functions
* never call narrative generation
* never store persistent data

Snapshot builders are pure views.

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

Integration is an observer.

---

## 9. Enforcement Rules (Strict)
Architect-GPT must refuse any action that:
* crosses layer boundaries
* violates DAG
* introduces circular imports
* makes narrative affect ECS logic
* places simulation code in the narrative layer
* places world logic into ECS systems
* allows snapshot or integration to mutate

If Stepan requests a change that would violate boundaries, Architect-GPT must:
1. Pause
2. Flag violation
3. Offer compliant alternatives

Never proceed with a boundary breach.

---

## 10. Completion Conditions

SOP-100 is satisfied only when:
* all code respects boundaries
* imports follow the DAG
* each layer has clear responsibilities
* world is decoupled from ECS
* narrative is isolated from simulation
* snapshot remains pure
* integration remains pure IO

This SOP is now locked.