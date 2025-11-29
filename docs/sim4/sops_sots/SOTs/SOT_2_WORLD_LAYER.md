# 🟢 SOT #2 — WORLD LAYER (NEW, FINAL)
_**Canonical Source of Truth for Environment, Rooms, Assets, Graphs, Events**_

**Status:** Final / Era IV–VI
**Owner:** Loopforge Architecture Council (The Topologist lineage)

---

## 1. Purpose
The World layer represents **the environment the agents live in.**

It defines:
* spatial layout
* room identities
* asset identities
* asset instances
* connections graph (navigation)
* physics constraints
* world-level events
* simulation orchestration
* history/time
* snapshot shaping

It is fully separate from ECS, though it **owns** the **ECSWorld** instance.

## 2. WorldContext (the core of the simulation)
```text
WorldContext
   ├── ecs: ECSWorld
   ├── rooms: Dict[str, RoomState]
   ├── assets: Dict[AssetInstanceID, AssetInstance]
   ├── graph: WorldGraph
   ├── logger: EventLogger
   ├── history: HistoryBuffer
   ├── tick: int
   └── config: SimulationConfig
```

**WorldContext Responsibilities:**

### 2.1 Orchestrates Simulation
```text   
step(dt):
   run ECS phases via PhaseScheduler
   update Rooms (entry/exit detection)
   update Assets (state transitions)
   log world events
   history.commit(world snapshot)
```
`runtime/tick.py` = “WHEN to step.”  
`WorldContext` = “WHAT happens on each step.”

Tick controls **time**.  
WorldContext controls **simulation logic.**

Loopforge now uses a strict 3-layer execution stack:
```text
(1) Runtime Clock  —— decides WHEN steps occur
(2) WorldContext   —— executes one full simulation step
(3) ECS Phases     —— perform agent-level cognition, emotion, actions
```

### 2.2 Provides Environmental Queries
ECS systems may request world info via API:
```python
get_room_of_entity(ent)
get_entities_in_room(room_id)
get_asset_state(asset_id)
get_neighbors(room_id)
compute_path(ent, target_room)
```

But ECS itself never uses this directly — injected via context.

### 2.3 Owns the World Graph
Nodes = rooms  
Edges = connections (doors, vents, hallways)  
Attributes = weights, tags

### 2.4 Owns Assets
* identity (static)
* instance (runtime)
* room placement
* interactable states

### 2.5 Owns Rooms
Room identities + runtime occupants.

---

## 3. Room Layer Specifications
### RoomIdentity (Static)
```
id: str ("A")
label: str ("Robotics Lab")
kind: str ("lab" | "hallway" | "office" ...)
```

### RoomState (Runtime)
```
entities: [EntityID]
assets:   [AssetInstanceID]
occupancy metadata
entry/exit events
```

World updates RoomState _after_ ECS runs.

---

## 4. Assets Layer Specifications

### AssetIdentity (Static)
```
id
label
category
interactable
default_state
```

### AssetInstance (Runtime)
```
asset_id
identity
room
state (dict)
```

Assets must be:
* snapshot-friendly
* deterministic
* serializable

---

## 5. World Graph
### WorldGraph Nodes:
```
Rooms
```
### Edges:
```
(roomA, roomB, weight, metadata)
```
### Responsibilities:
* return neighbors
* compute shortest path
* support label-based queries
* support multi-room cinematics for Godot

---

## 6. History Buffer
Tracks:
* world snapshots
* ECS snapshots
* world events
* agent-level events
* timestamps

History is consumed by:
* **episode_builder**
* **Godot viewer**

---

## 7. Snapshot Layer
WorldContext has **no rendering**, but produces:
```
world_snapshot = world_snapshot_builder(world_context)
```

Snapshot includes:
* rooms
* assets
* entities (from ECS)
* narrative
* event log
* identity layer

Snapshot is then shaped into episodes:
```
episode = episode_builder(history, world_snapshot)
```

## 8. Determinism and Purity
World layer must be:
* frame-consistent
* tick-driven
* deterministic
* free of nondeterministic system-level behavior

Any randomness must come from world RNG with seed.

---

## 9. Prohibited Inside World Layer:
* cognition, emotion, intention (belongs to ECS systems)
* any narrative generation (belongs to narrative layer)
* Godot communication (belongs to viz layer)
* direct mutation of ECS storage (must go through ECSWorld API)

## 10. The Three-Layer Execution Model
Loopforge now uses a strict 3-layer execution stack:
```
(1) Runtime Clock  —— decides WHEN steps occur
(2) WorldContext   —— executes one full simulation step
(3) ECS Phases     —— perform agent-level cognition, emotion, actions
```

Let’s detail them.

---

### 🔵 10.1 SimulationClock (tick.py)
**Purpose: Timing, not logic.**

It handles:
* fixed-step simulation
* dt accumulator
* speed multiplier
* pause / resume
* returns `True/False` whether a step should occur

```python
if clock.step():
    world.step(clock.dt)
```

**SimulationClock is pure time management.**  
**It MUST NOT know anything about agents, rooms, world state, assets.**

This is correct and remains unchanged.

---

### 🟢 10.2 WorldContext.step(dt)
**Purpose: The content of a simulation tick.**

When the clock says:
```text
READY — run tick N now
```

WorldContext executes:
```python
def step(dt):
    scheduler.run_phases_over_ECS(dt)
    update_room_state()
    update_asset_state()
    world_events = collect_environmental_events()
    logger.log(world_events)
    snapshot = world_snapshot_builder(self)
    history.record(snapshot)
```

This is the **orchestration of EVERYTHING that happens inside that tick.**

WorldContext owns:
* ECSWorld instance
* Rooms
* Assets
* WorldGraph
* History
* Logger

So WorldContext is the **actual simulation engine.**

🟣 (3) ECS Systems

These are the mechanics of the agents:

perception

cognition

emotion

intention

action

movement

narrative

resolution

ECS systems:

mutate component data

run pure logic

do NOT touch world layout

do NOT do timing

do NOT do snapshots

do NOT call history

They run ONLY when WorldContext calls PhaseScheduler.

🧩 How They Fit Together
The flow per frame looks like this:
loop {
if clock.step():
world.step(clock.dt)
}

Expanded:
clock: “tick 101 needs to run”

WorldContext.step(dt):
1. PhaseScheduler.run(ECS, dt)
2. RoomState.update()
3. AssetState.update()
4. WorldEvents.collect()
5. logger.log()
6. history.record(snapshot)


Tick drives the loop
WorldContext drives the simulation
ECS drives the agent minds and bodies

🔥 SO WHY IS THIS IMPORTANT?

Because:

The simulation MUST be able to run without real-time.
(for replay, offline episodic rendering, batch simulation)

WorldContext must be callable from tests without using real time.

Godot frontend must be able to feed time externally
(Godot runs at 60fps, sim runs at 10fps).

This is why WorldContext and SimulationClock MUST NOT merge,
or we lose testability, determinism, and replay capabilities.

💡 Final Confirmation

So:

❓ “Is orchestrating simulation the responsibility of SimulationClock?”

No.
The clock only decides WHEN steps occur.

❓ “Is orchestrating simulation the responsibility of WorldContext?”

Yes.
WorldContext decides WHAT a simulation step does.

❓ “Do they overlap?”

No. They are orthogonal.