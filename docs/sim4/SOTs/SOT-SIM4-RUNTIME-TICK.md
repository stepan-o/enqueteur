# 📘 SOT-SIM4-RUNTIME-TICK
_**Deterministic Tick, Phase Scheduler & Runtime Contracts**_  
**Draft 1.0 — Architect-Level, Rust-Aligned**

---

## 0. Scope & Purpose
This SOT defines the **runtime/tick architecture** of Sim4:
* how the **SimulationEngine** advances time
* how **phases** are ordered and executed
* how **ECS**, **world**, and **narrative** are orchestrated
* where **mutation is allowed** and how it happens
* how **RNG** integrates into the tick (diff/history/replay are planned)
* how this stays compatible with **SOP-000**, **100**, **200**, **300**, and **SimX vision**

It is the canonical spec for:
* runtime/tick.py (implemented)
* runtime/clock.py (implemented)
* runtime/scheduler.py (implemented)
* runtime/command_bus.py (implemented)
* runtime/events.py (implemented)
* runtime/narrative_context.py (implemented)
* planned: runtime/engine.py, runtime/diff.py, runtime/history.py, runtime/replay.py
* contracts with ecs/, world/, narrative/, snapshot/.

**Implementation status (current repo):**
- `tick.py` is the only orchestrator; there is no `engine.py`.
- Phase H emits a `WorldSnapshot` to `snapshot/output.py::TickOutputSink` if provided.
- Offline exports and live envelopes are wired by `host/sim_runner.py` (outside the SOP-100 DAG).

---

## 1. Runtime’s Role in the 6-Layer DAG
Per **SOP-100**, the engine DAG is:
```text
Kernel:   runtime → ecs
         runtime → world
         runtime → snapshot → integration
         runtime → (read-only views) → narrative
narrative → (suggestion queues) → runtime (Phase A integration ONLY)
```

In this DAG:
* `runtime/` is the **orchestrator**:
  * owns the **tick loop**
  * calls ECS systems in deterministic order
  * calls **WorldContext** subsystems
  * triggers snapshot building
  * triggers narrative **after** the deterministic tick
* `runtime/` **does not**:
  * store ECS component data
  * call narrative directly for simulation decisions
  * contain semantic cognition
  * run LLMs

Runtime is the **conductor**, not a player.

---

## 2. Core Runtime Modules
Runtime consists of:
* `tick.py`
  * `tick(...)` — canonical tick pipeline
* `clock.py`
  * `TickClock`, `DeltaTime`
* `scheduler.py`
  * `PhaseScheduler`: maps phases → ECS systems
* `command_bus.py`
  * ECS/world command batching + sequencing
* `events.py`
  * `GlobalEvent`, `LocalEvent`, `EventBus`
* `narrative_context.py`
  * NarrativeRuntimeContext + DTOs

Planned (not implemented):
* `engine.py`, `diff.py`, `history.py`, `replay.py`, `episode.py`, `world_context.py` façade

Runtime does **not** live in any other folder; other layers never import it.

---

## 3. Canonical Tick Phases (SOP-200 Aligned)

The tick pipeline is **strict and ordered**:
```text
tick(dt):
    1. Lock WorldContext
    2. Update Clock
    3. Phase A: Input Processing
    4. Phase B: Perception
    5. Phase C: Cognition (non-LLM)
    6. Phase D: Intention → ECS Commands
    7. Phase E: ECS Structural Commit & Command Application
    8. Phase F: World Updates
    9. Phase G: Event Consolidation
    10. Phase H: Snapshot emission (TickOutputSink)
    11. Phase I: Narrative Trigger (post-tick)
    12. Unlock WorldContext
```

**Mutations per SOP-200 (Option A alignment):**
* ECS component writes: Phases **B–E** (deterministic ECS systems)
* Phase **E**: structural commit + buffered command-batch application (entity create/delete, component add/remove, global ECSCommandBatch)
* World mutations: **Phase F** (via WorldContext.apply_commands(...))
* History/diff: **Phase H** (snapshot emission only in current code)
* Narrative: **Phase I** (semantic only, no kernel mutation)

All other phases are **pure** (read-only or buffering only).

Note (Phase H): Phase H emits a WorldSnapshot to an optional `TickOutputSink`. No TickFrame adapter exists in current code.

---

## 4. Phase-by-Phase Specification

---

### 4.1 Phase A — Input Processing
**Responsibility:**  
Collect and normalize **all external and cross-layer inputs** for this tick.

Sources include:
* player / external control inputs (if any)
* scripted scenario events
* **semantic suggestions** from the last tick’s narrative:
  * `IntentSuggestions`
  * `GoalSuggestions`
  * belief/plan hints
* debug / dev tools (e.g. test harness steps)

**Output:**
* A normalized, deterministic **InputBundle** for this tick:
  * sorted by source then by timestamp/ID for deterministic order
* Updates to:
  * **ECS-side command buffers** for `PrimitiveIntent` injection
  * scenario triggers/flags for this tick in runtime

Constraints:
* No **ECS storage** or **world state** mutation in Phase A (only input normalization + command buffering).
* All ordering is **stable** (e.g., by agent ID, then source priority).
* RNG calls (if any) go through `util/random.py` and are logged.

---

### 4.2 Phase B — Perception
**Responsibility:**
Update **perception substrate** (L1/L2) in ECS using **read-only** world views.
* Runtime builds **PerceptionViews** using `WorldContext`:
  * what each agent could see / hear / sense
  * occlusion, distance, line-of-sight
* `PhaseScheduler` calls `PerceptionSystem` (and any other Phase-B systems):

```text
perception_system.run(ecs_world, world_views.perception_view, dt, rng)
```

Allowed:
* ECS component updates:
  * PerceptionSubstrate: visibility lists, salience, attention slots
* Queries into world/ strictly via views (no imports of world in ECS).

Forbidden:
* World mutation
* Narrative calls
* I/O

---

### 4.3 Phase C — Cognition (Non-LLM)
**Responsibility:**  
Update **cognitive substrates** deterministically:
* beliefs
* drives
* emotion fields
* motives
* plan stubs
* social weights

Systems typically run in this order (all in Phase C):
1. `CognitivePreprocessor`
2. `EmotionGradientSystem`
3. `DriveUpdateSystem`
4. `MotiveFormationSystem`
5. `PlanResolutionSystem`
6. `SocialUpdateSystem`

Each system:
* Reads ECS state and possibly **read-only world views** (e.g., crowd tension)
* Writes **only numeric / structural substrates** (as per SOP-300)
* Uses deterministic RNG via `util/random.py` if needed (e.g., tiebreaking)

**Forbidden:**
* semantic meaning-making
* narrative calls
* world mutation
* movement/action resolution

---

### 4.4 Phase D — Intention → ECS Commands
**Responsibility:**
Turn motives + external suggestions into **sanitized action commands**.

Steps:
1. **IntentResolverSystem**
   * Reads:
     * `PrimitiveIntent` (created from:
       * narrative `IntentSuggestions`
       * player inputs
       * scripts / scenario triggers)
     * PlanLayerSubstrate
     * DriveState
   * Writes:
     * `SanitizedIntent` (still abstract but validated)
2. Runtime prepares **movement + interaction views**:
   * e.g., navigation constraints, occupancy info from `WorldContext`
   * passed to ECS systems as **read-only world views**
3. `MovementResolutionSystem`
   * Reads: `SanitizedIntent`, Transform, nav views
   * Writes: `MovementIntent`, `PathState`, `ActionState` (movement modes)
4. `InteractionResolutionSystem`
   * Reads: `SanitizedIntent`, target info views
   * Writes:
     * `InteractionIntent`, `ActionState`  
     * buffered **WorldCommands** (e.g., `OpenDoor`, `ToggleMachine`) into a **world command buffer** owned by runtime

**Note:**
No world mutation yet. ECS systems may write intent/movement/interaction substrates deterministically in Phase D; structural ECS commits (entity lifecycle, component add/remove, global command application) remain reserved for Phase E.

---

### 4.5 Phase E — ECS Structural Commit & Command Application

**Responsibility:**
Finalize ECS-side mutations for this tick by applying buffered command batches and performing structural commits.

Here, systems that **actually write to ECS storage** run, using command buffers and substrate updates prepared in previous phases.

Key actors:
* `ActionExecutionSystem`
  * Reads:
    * `MovementIntent`, `InteractionIntent`, `ActionState`
  * Writes:
    * `Transform`, `RoomPresence`, `PathState`
    * short-term memory counters
    * possibly additional world commands into the world command buffer
* Any other ECS mutation systems that must write after intent resolution  
(e.g. inventory state changes that are purely agent-side).

**Rules:**
* All ECS structural commits and command-batch applications must be completed by the end of Phase E.
* No world mutation here; only emission of world commands (to be applied in Phase F).

---

### 4.6 Phase F — World Updates

Responsibility:
Apply world-side mutations via WorldContext using commands from ECS.

Runtime:

Collects WorldCommands emitted in Phase D/E:

MoveAgent

OpenDoor

SpawnItem / DespawnItem

ToggleMachine

etc.

Passes them to WorldContext:

world_context.apply_commands(world_commands, dt, rng)


WorldContext dispatches to world subsystems:

room manager

asset manager

navgraph adjusters (if dynamic)

world events

Constraints:

world/:

cannot mutate ECS directly

must be deterministic

must use stable iteration order

Runtime ensures WorldCommands are:

applied in stable order (e.g. sorted by (tick, sequence_index)),

fully processed before moving to Phase G.

4.7 Phase G — Event Consolidation

Responsibility:
Aggregate ECS events + world events into a stable event log for this tick.

Sources:

ECS systems may emit events (e.g. AgentEnteredRoom, AgentSpoke, PlanUpdated).

World subsystems may emit events (e.g. DoorOpened, ShiftChangeStarted).

runtime/events.py provides:

GlobalEvent, LocalEvent

EventBus with deterministic ordering

Runtime:

collects all events

assigns final (timestamp, sequence) IDs

pushes them into the EventBus and interim structures for history/diff/snapshot

No simulation state mutation occurs here — events are just records.

4.8 Phase H — Snapshot emission (read-only)

Responsibility:
Build a `WorldSnapshot` and emit it to an optional `TickOutputSink`. This is
strictly read-only (no simulation mutation).

Runtime performs the following steps in Phase H:

1. Build a `WorldSnapshot` via `snapshot/world_snapshot_builder.py`.
2. If a `TickOutputSink` is provided, call `on_tick_output(...)` (best-effort; exceptions are swallowed).

Constraints:
* No kernel mutation (runtime/ecs/world state).
* No I/O or RNG.
* No direct dependency on integration types.

Note:
- `runtime/diff.py`, `runtime/history.py`, and `runtime/replay.py` are **not implemented**.
- Offline exports and replay artifacts are produced by `host/sim_runner.py` using
  `integration/export_state.py` (KVP-0001 envelopes).

4.9 Phase I — Narrative Trigger (Post-Tick)

Responsibility:
Kick off narrative sidecar on a fully deterministic snapshot.

Runtime:

Uses snapshot/builder.py to create:

WorldSnapshot

AgentSnapshots

optional tick-local summary (e.g. events, tension fields)

Passes the snapshot (or compressed views) to narrative/pipeline.py:

either immediately

or via a queue (for async LLM processing, outside tick)

Narrative then:

performs reflection (L6), dialog, inner monologue, etc.

writes only to:

narrative-local memory

ECS NarrativeState (semantic fields only)

future IntentSuggestions / GoalSuggestions via narrative/adapters.py

Runtime:

never waits on LLM calls inside tick.

treats narrative as post-tick, out-of-band for determinism.

5. PhaseScheduler Contract

runtime/scheduler.py defines:

PhaseScheduler, which knows:

all ECS systems

their assigned phases (B–E)

their ordering within phases (stable, explicit)

E.g. (conceptual):

PHASE_SYSTEMS = {
"B": [PerceptionSystem],
"C": [CognitivePreprocessor, EmotionGradientSystem, DriveUpdateSystem,
MotiveFormationSystem, PlanResolutionSystem, SocialUpdateSystem],
"D": [IntentResolverSystem, MovementResolutionSystem, InteractionResolutionSystem],
"E": [ActionExecutionSystem, InventorySystem],
}


The scheduler:

never introspects world or narrative

never adds systems dynamically

preserves order across runs and machines

This is critical for replay and Rust migration.

6. RNG & Determinism in Runtime

Per SOP-200:

All randomness must go through util/random.py:

rng = SimulationRNG(seed)
rng.next_float()
rng.next_int()
rng.substream("perception")   # optional structured sub-streams


Runtime’s responsibilities:

Initialize SimulationRNG with scenario seed.

Provide sub-RNGs to:

ECS systems

world subsystems

Log RNG usage per tick for replay if needed.

Forbidden:

random module

numpy.random

time-based seeds

OS entropy

7. Replay Contract (planned)

Replay modules (`runtime/replay.py`) are **not implemented** in current code.
For offline artifacts, replay-style verification is performed in
`integration/export_verify.py`, which reconstructs state by applying KVP diffs
from `manifest.kvp.json` and validates the step_hash chain.

8. Interaction with Other SOTs & SOPs

This SOT must obey:

SOP-000 (Architect AOC)

Any mutation in tick structure requires a revision cycle, not ad-hoc change.

SOP-100 (Layer Boundaries)

runtime does not store ECS components.

world/ never calls ECS.

narrative is post-tick, cannot affect phases B–F.

SOP-200 (Determinism)

Tick phases, RNG usage, ordering.

SOP-300 (ECS Substrate)

Phases B–E implement the substrate updates as defined there.

It also aligns with:

SOT-SIM4-ENGINE (folder structure + responsibilities)

Free Agent Spec (agent mind dynamic flows).

9. Completion Condition for SOT-SIM4-RUNTIME-TICK

This SOT is considered implemented and respected when:

SimulationEngine.tick() adheres to the 9 phases defined above.

All ECS systems are assigned to B–E via PhaseScheduler with explicit order.

WorldContext processes world commands only in Phase F.

No kernel state mutation occurs outside:
* ECS component writes in **Phases B–E**
* ECS structural commits + command-batch application in **Phase E**
* World mutations in **Phase F**

Narrative is triggered only after Phase H.

Replay/diff logging is planned but not yet implemented in runtime.

At that point, the runtime tick is SimX-safe:
we can scale up worlds, agents, and narrative complexity without breaking determinism or Rust portability.
## 10. Sprint 6 Implementation Status (Sim4 Runtime Tick)

As of Sprint 6 (2025-12-01), the following runtime tick behavior is implemented in the Python prototype:

- `tick(...)` in `backend/sim4/runtime/tick.py` implements phases A–I in order, with:
  - Phase A: stub input processing (no real InputBundle yet).
  - Phases B–D: generic system phases using a `system_scheduler.iter_phase_systems(phase)` contract, with deterministic `SimulationRNG` seeding per system based on `(rng_seed, tick_index, system_index)`.
  - Phase E: ECS command application via `ECSCommandBatch` (global seq 0..N-1 in aggregated order) and `ECSWorld.apply_commands(...)`.
  - Phase F: World command application via `WorldCommandBatch` (global seq 0..N-1) and `apply_world_commands(...)` from `backend.sim4.world.apply_world_commands`, emitting `WorldEvent` values.
  - Phase G: Event consolidation into a flat `RuntimeEvent` list via `backend.sim4.runtime.events::consolidate_events(...)` (ordering policy: world → ecs → runtime, each in provided order).
  - Phase H: builds a WorldSnapshot and emits it to an optional `TickOutputSink` (best-effort; no diff/history persistence in runtime).
  - Phase I: calls the narrative bridge if provided (exceptions swallowed to preserve determinism).

Deviations from the long‑term design in this SOT (pragmatic for Sprint 6):

- The runtime‑level `WorldContext` façade (defined by SOT‑SIM4‑RUNTIME‑WORLD‑CONTEXT) is not implemented yet:
  - `tick(...)` currently consumes `backend.sim4.world.context.WorldContext` directly.
- Phases B/C/D are not yet specialized/renamed as Perception/Cognition/Intention:
  - The scheduler simply executes configured system types for phases "B", "C", and "D".
- History/diff/replay modules:
  - No `runtime/diff.py`, `runtime/history.py`, or `runtime/replay.py` exist yet; Phase H currently performs snapshot + `TickOutputSink` emission only. Persistent diff/history/replay remain pending.
  - Offline artifacts are exported by host orchestration (`host/sim_runner.py`) using `integration/export_state.py`.
- Narrative integration:
  - Phase I calls `NarrativeRuntimeContext` if it is passed into `tick(...)`; this remains optional and best-effort.

Determinism & layer boundaries satisfied in Sprint 6:

- SOP‑200 determinism:
  - ECS component writes occur in Phases B–E (systems), with structural commits and command-batch application confined to Phase E; world mutations are confined to Phase F.
  - RNG usage is deterministic and injected into systems via `SimulationRNG` using explicit seeding.
  - Command and event ordering is stable (policy is documented and covered by tests).
- SOP‑100 layer boundaries:
  - runtime orchestrates ECS + world and does not store component data.
  - world does not import ecs or runtime; systems access world only via read‑only views.

### Sprint 6 Readiness for Sprint 7/8

The current runtime tick implementation is considered:

> ✅ Ready for Sprint 7 (snapshot layer) and Sprint 8 (narrative bridge)

in the sense that:

- A deterministic per‑tick `TickResult` is available, containing:
  - `tick_index`, `dt`
  - the ECS commands applied during Phase E
  - the world outcomes of Phase F via `WorldEvent` list
  - consolidated runtime events (`List[RuntimeEvent]`) suitable for history/snapshot/narrative.
- Future snapshot builders can safely read ECS and world state after Phase F, using the same tick’s `tick_index`.
- Narrative can be wired as a Phase‑I sidecar once snapshot builders are in place.
