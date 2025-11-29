# 🌆 LOOPFORGE ERA X: EMERGENT NARRATIVE CITY ENGINE
_**A Forward-Compatible Architecture for Sim4 → SimX (Rust Transition Included)**_

_Draft v0.1 — STEPAN_LEVEL +20_

---

## 📌 Executive Summary

Loopforge’s long-term vision requires a simulation engine with these properties:
### 1. Deterministic, high-performance world simulation (Rust)
* Tick-based, replayable
* Pure ECS + spatial indexing
* Diff streams for remote viewers
* Serialization stable across versions

### 2. LLM-powered agent intelligences
* Modular “seven-layer mind”
* Local, persistent internal personality state
* Emergent goals
* Memory with compression, salience, forgetting
* Cognitive dynamics (curiosity, tension, mood drift)
* “Self-models” (metacognition)
* Narrative reflectors (inner monologue, justification)

### 3. Godot or Godot-like viewer
* 2.5D isometric (Disco Elysium vibe)
* Character bubbles (dialogue / inner monologue)
* City-level visualization of “psycho topology”
* Replay viewer (rewind, zoom timeline)

### 4. Emergent narrative pipeline
* City-wide story arcs
* Character arcs
* Day/night cycle
* Social network dynamics
* Emotional tension maps
* Player indirect influence via “world nudges”

### 5. Sandbox world with multi-room simulation
* Streets, zones, plazas, interiors
* Rooms loaded/unloaded
* Agents moving across zones
* Simulated sensory perception
* Ambient events, weather, traffic

Sim4 must be architected not as a final system but as the **first robust rung of that ladder**.  
The design must scale **linearly** to Rust, not collapse under its own weight.

The document below rewrites the **Sim4 specification** with explicit support for future _**SimX**_.

---

## 🧠 1. Core Principle: Dual-Engine Architecture
The final Loopforge engine consists of two distinct but synchronized engines:

---

### 1.1. Simulation Kernel (Rust, deterministic)
This engine handles:
* ECS
* physics-like movement
* time
* event propagation
* world geometry / rooms
* pathfinding
* sensory perception
* memory traces (raw events)
* conflict resolution
* social graph updates
* internal emotional gradients (numerical)

It does **not** run LLMs.
It does **not** do narrative.
It does **not** do reflection.

It is deterministic and replayable:
```
input seed + events => same future
```

This kernel is what Sim4 Python is prototyping.

---

### 1.2. Narrative Mind Engine (Python/LLM sidecar, non-deterministic)
This engine handles:
* meaning-making
* dialog generation
* internal monologue
* blending short- and long-term goals
* personality drift
* reflection on events
* justification of actions
* hallucinated memories (with guardrails)
* emergent “quests” or “desires”
* poetry, inner symbolism, metaphors
* mind-to-mind interactions

It receives:
* history buffer slice
* current emotional state
* social relationships
* perception log
* conflicts
* goals

It outputs:
* new goals
* narrative lines
* emotional reactions
* personal interpretations
* beliefs
* biases
* desires
* rumors
* dialogue to speak
* inner monologue for UI
* world-affecting “intentions”

This is how Disco Elysium vibes get created but **emergent**.

---

## 🏗️ 2. Structural Requirements for Sim4 (Python, transitional)
Sim4 architecture must meet the following criteria:

---

### 2.1. Hard Separation of Modules
```text
sim4/
    runtime/         # deterministic tick engine
    ecs/             # pure ECS (storage, systems)
    world/           # rooms, assets, graphs, state
    narrative/       # LLM cognition + memory shaping
    snapshot/        # world → Godot renderer
    integration/     # Godot server, API endpoints
```

This separation **mirrors** the final Rust architecture:
```
loopforge_engine/
    ecs/
    kernel/
    world/
    scheduler/
    snapshot/
    ffi/
```

Python Sim4 becomes the “blueprint” for its Rust successor.

---

### 2.2. ECS must be “Rust-clean”
* strict data ownership
* stable component types
* SOA layout
* archetype-based grouping
* no Python dynamic typing in core loops
* avoid Python mutation patterns that won’t map to Rust

Sim4 ECS should be the **superset** of the Rust ECS features.

---

### 2.3. WorldContext owns everything except agent minds
WorldContext must coordinate:
1. tick
2. movement
3. collisions
4. room entry/exit
5. sensory perception
6. world events
7. history
8. snapshot building
9. time-of-day
10. weather
11. ambient events

It must not run cognition.  
Cognition is delegated to the narrative engine.

---

## 🏙️ 3. Requirements for Disco-Elysium-Scale Simulation
**(These shape what Sim4 must support.)**

---

### 3.1. Multi-Agent Social Physics
Agents must:
* form opinions
* form relationships
* break them
* form factions
* shift allegiances
* perceive each other
* misperceive each other
* spread rumors
* grow jealous or afraid
* escalate conflict
* defuse conflict
* set goals
* drop goals
* influence others
* be persuaded
* be manipulated

Sim4 must therefore support:

#### Component groups
* EmotionalState
* CognitiveState
* SocialState
* IntentState
* ActionState
* Perception
* Memory
* ProfileTraits
* NarrativeState

#### System groups
* perception
* cognition (deterministic “preprocessing”)
* emotion gradient
* intention formation
* action state resolution
* social update
* event integration

LLM minds attach on top of this.

---

### 3.2. City-Level Emergent Narrative
Needs:
* room graph
* day cycles
* weather events
* ambient patterns
* crowd simulation
* spatial tension maps
* time series for emotional flux

Sim4 → SimX must generate city-wide storylines such as:
* “tension slowly rises between faction A and faction B”
* “Agent X has growing paranoia”
* “Room Y becomes a hotspot of gossip”
* “Agents avoid the plaza due to last night’s fight”
* “A rumor of sabotage spreads across districts”

This comes from simulation, not scripts.

---

## 🔥 4. The Sim4 Engine Spec (Rust-Oriented Redesign)

Below is the rewritten Sim4 spec for long-term health.

---

### 4.1. sim4/runtime/
A Rust-compatible deterministic kernel.

#### Must include:
**engine.py**
* init
* run_tick
* run_for_duration
* run_until_condition
* hooks (before/after tick)
* world integration

**scheduler/**
* PhaseScheduler
* PhaseOrder linearization
* deterministic schedule

**time/**
* Clock
* TickRate
* delta-time smoothing

**history/**
* ring buffer
* diff stream
* event log
* replay builder

**events/**
* event bus
* global events
* local events

This folder must match Rust 1-to-1.

---

### 4.2. sim4/ecs/
The ECS must exactly map to Rust ECS layout.

#### Required:
* archetype storage
* pure SOA
* no Python trickery
* minimal indirection
* stable IDs
* query language
* world-level entity manager

---

### 4.3. sim4/world/
Represents the environment.

#### Required:
* static identity (rooms, buildings, zones)
* runtime state (occupancy, temperature, tension)
* world graph (navigation)
* assets (objects)
* event generators (ambient patterns)
* CPUs for environmental systems

---

### 4.4. sim4/narrative/
This is the non-deterministic mind engine.

#### Required:
* narrative generator
* reflective memory
* LLM policy adapters
* belief revision
* intention generation
* inner monologue
* dialog shape
* personality drift

This module must:
* operate asynchronously
* interface via stable contracts
* never block simulation
* produce “suggested” goals
* feed deterministically into simulation via sanitized intent updates

---

### 4.5. sim4/snapshot/
Stable viewer API.

#### Required:
* world snapshot builder
* agent snapshot builder
* narrative projection
* diff adapter

Snapshots feed Godot.

---

## 🧬 5. How Sim4 Grows Into SimX
Below is the trajectory:

---

### Sim4 (now)
clean ECS
* room/world separation
* stable snapshot API
* narrative hooks (minimal)
* deterministic engine

---

### Sim5
* emotional field simulation
* city-scale tension
* room-level gossip propagation
* proper memory architecture
* cognitive preprocessor

---

### Sim6
* real social networks
* rumor engines
* persuasion models
* conflict dynamics
* faction modeling

---

### Sim7
* temporal arcs
* character lifepaths
* generational memory
* city-wide narrative layers

---

### Sim8
* autonomous quests
* self-directed goals
* long-term ideals
* moral drift

---

### Sim9
* neural personalities
* fully adaptive character arcs
* emergent ideology formation

---

### SimX
* Disco Elysium but emergent
* full “mind theatre” (inner monologue)
* city of psychoactive robots
* real historical development
* Plural collective consciousness
* player is an indirect god over a living robot society or a stranger walking the streets barely able to affect outcomes

---

## 🏁 Conclusion:
The architecture absolutely **must** follow the Rust-oriented dual engine model above.  
Sim4 is the prototype of the deterministic kernel.  
Narrative remains separate.  
Agents evolve to full “7 Layer Minds.”  
The city becomes a socio-narrative machine.

This spec is future-proof, Rust-friendly, Godot-compatible, and capable of scaling to your Disco Elysium dream.