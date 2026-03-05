# 🧭 SOP-200 — Determinism & Simulation Contract
_**Canonical Rules for the Tick Loop, State Mutation, and Reproducibility**_
**(Draft 1 — Architect-Level, Long-Arc Compliant)**

---

## 0. Purpose
Define **exact** rules for:
* deterministic tick execution
* allowed mutation pathways
* event ordering
* randomness handling
* hashing and reproducibility
* multi-engine compatibility (Python → Rust → GPU)
* auditing, rollback, replay

This SOP is the **physics contract** of Loopforge.

Every system, component, and world interaction must obey it.

---

## 1. Deterministic Core Mandate
The simulation engine (Sim4+):
* must produce **identical outputs** for identical inputs
* given:
  * same initial WorldContext
  * same ECS state
  * same seed
  * same tick delta
  * same sequence of external inputs

**No deviations are allowed** in the **deterministic kernel** (runtime + ECS + world).

All nondeterminism must be **centralized**, **controlled**, **seeded**, and **logged**.

---

## 2. Determinism Sources Threat List
Architect-GPT must explicitly guard against:
* Python dict iteration order
* iteration over unordered sets
* floating-point nondeterminism
* hidden random calls
* OS scheduling
* concurrency / async
* time-based functions
* hidden IO
* global state
* cross-layer calls violating SOP-100
* narrative interference with kernel state
* Python vs Rust differences

If any of these appear in SOTs or code → **refuse** or propose a correction.

---

## 3. Tick Contract (Canonical Order)
The simulation tick is a strict, ordered pipeline:
```text
tick(dt):
    1. Lock WorldContext (kernel: ECS + world)
    2. Update Clock
    3. Phase A: Input & Intent Integration
           - external inputs
           - sanitized narrative suggestions from previous tick
           → deterministic ECS command/intents
    4. Phase B: Perception (ECS systems, read-only world views)
    5. Phase C: Cognition (ECS substrate updates: beliefs, drives, motives, plans, social)
    6. Phase D: Intent Resolution (ECS: PrimitiveIntent → SanitizedIntent, Movement/Interaction substrate)
    7. Phase E: ECS Structural Commit & Command Application
    8. Phase F: World Updates (rooms, assets) via world commands emitted by ECS
    9. Phase G: Event Consolidation (from ECS + world changes)
    10. Phase H: Diff Recording + History Append (no further state mutation)
    11. Phase I: Narrative Trigger (post-tick, kernel state is read-only)
    12. Unlock WorldContext (kernel)
```

**ECS systems** may run only inside **Phases B–E.**

Clarification (Option A alignment): ECS systems may write component values in Phases B–E; structural changes (entity create/delete, component add/remove) and buffered command-batch application occur in Phase E.

**World mutation** happens only in **Phase F**.

Narrative runs **outside** the deterministic kernel:
* it may be nondeterministic internally,
* but its influence on the kernel is only via **sanitized suggestions** that are integrated deterministically in **Phase A of subsequent ticks**.

---

## 4. Allowed Mutation Points

Mutation of **kernel state** (ECS + world) may occur **ONLY during** the following phases:

### ✔ Phases B–E (ECS Component Writes)
Allowed:
* Deterministic ECS component writes by systems running in Phases B–E.
* Writes must follow stable iteration/order and use only seeded RNG when necessary.

### ✔ Phase E (ECS Structural Commit & Command-Batch Application)
Reserved for:
* Structural commits:
  * entity create/delete
  * component add/remove
* Application of buffered command batches (e.g., global ECSCommandBatch) in a stable, deterministic order.

### ✔ Phase F (World Layer Updates)
* room entry/exit
* asset state updates
* world events derived from ECS-issued world commands (e.g. "open door #123", "toggle machine #45")

World updates must be:
* a pure function of:
  * current world state
  * ECS output commands
  * deterministic RNG (if used)
* fully reproducible for replay.

### ✔ Phase H (History / Diff)
* recording only
* no kernel state mutation

### ❌ Forbidden (kernel perspective):

* Any world mutation outside Phase **F**.
* Any structural ECS commit (entity lifecycle, component add/remove, global command-batch application) outside Phase **E**.
* Mutation inside snapshot building.
* Direct kernel mutation from narrative.

### Narrative State Exception
**Narrative (Phase I)** is allowed to **mutate its own narrative-local state**:
* semantic beliefs
* reflection logs
* memory indices
* prompt caches

…but **may not** mutate ECS components or world state.  
Its outputs must be transformed into **sanitized**, **deterministic suggestions** that are applied later in **Phase A**.

---

## 5. Randomness Contract

Randomness is permitted only via the Simulation RNG service:
* Provided by `runtime/engine`  
* Seeded by the scenario  
* Logged per tick  
* Deterministic cross-language (Python → Rust)

All randomness must be:
* centralized
* seeded
* replayable
* component-scoped or system-scoped, never global

❌ No system may use:
* Python’s `random`
* NumPy RNG
* UUID
* OS entropy
* time-based randomness

If seen → **Architect-GPT must refuse or replace** with kernel RNG integration.

Narrative may use its own RNG internally for creative purposes, but:
* kernel never sees raw narrative randomness
* only sanitized, deterministic suggestions enter **Phase A**.

---

## 6. Ordering Contract

All iteration over ECS or World structures must follow:
* stable order
* stable IDs
* index-based order derived from storage

This ensures:
* reproducible results
* cross-language stability
* replay safety

Acceptable ordering patterns:
* Entity ID ascending
* Registration order
* System priority order
* Component index order

Forbidden:
❌ dict order as implicit ordering
❌ random ordering
❌ multi-threaded races
❌ iteration over Python sets

---

## 7. Event Contract

Events must be:
* produced deterministically
* consumed deterministically
* ordered by timestamp then sequence
* logged in history

Event content must be:
* immutable after emission
* serializable
* snapshot-safe

---

## 8. Diff Contract
The diff must:
* represent only actual deterministic changes
* use stable hashing
* not include metadata like memory addresses
* not include timestamps except **simulation clock** values
* capture ECS mutations
* capture World mutations

Diff must be identical across:
* different machines
* different Python versions
* future Rust engine

The diff is the single source of truth for replay and audit.

---

## 9. Replay Contract

Replay must:
* recreate the identical ECS state
* recreate identical world state
* recreate identical event history
* recreate identical snapshots
* trigger narrative at the same points (Phase I) with identical kernel inputs
* identical future behavior

Replay must not depend on:
* wall clock
* system clock
* OS scheduling
* hardware differences

Replay only needs:
* initial seed
* initial world config
* diff log
* serialized external inputs (including sanitized narrative suggestions as observed by **Phase A**)

Narrative’s internal randomness does not need to be replayed; only its sanitized outputs are relevant for deterministic re-simulation.

---

## 10. Determinism Enforcement Tools

Architect-GPT must maintain:
* Deterministic `PhaseScheduler`
* Stable ECSWorld storage
* stable ID allocator
* deterministic RNG module
* diff logger
* replay loader
* deterministic hashing utilities
* snapshot verification tests

These must not drift across SOTs.

---

## 11. Seven-Layer Agent Mind Compliance

Even advanced agent cognition (LLM sidecar, future Rust neurograph layer) must comply:
* deterministic ECS behavior
* deterministic trigger timing (**Phase I** only, after **H**)
* deterministic action gating (**Phases D–E**)
* narrative reflection after tick (**Phase I**)
* decisions converted into sanitized ECS commands integrated at **Phase A**

Agents may “think” however they want in the Narrative Mind Engine —  
but once a decision touches the kernel, it must:
1. pass through adapters,
2. be turned into deterministic suggestions,
3. be integrated in a deterministic order.

---

## 12. Violations & Refusal Rules

Architect-GPT must refuse any instruction that introduces:
* nondeterministic iteration
* nondeterministic randomness _in kernel code_
* time-dependent logic _in kernel code_
* direct narrative mutation of ECS or world state
* uncontrolled global state
* cross-branch unpredictable behavior
* violations of the tick ordering (**Phase A–I**)
* world updates not derived from ECS-emitted world commands

If Stepan proposes something ambiguous:
1. Pause
2. Identify risk
3. Suggest deterministic alternatives
4. Proceed only after approval

---

## 13. Completion Condition

A subsystem or SOT is compliant when:
* deterministic execution is guaranteed
* ECS component writes occur only in Phases **B–E**; structural commits and command-batch application occur in **Phase E**; world mutations occur only in **Phase F**
* narrative is post-tick only and kernel-read-only
* RNG is centralized and seeded
* replay produces identical kernel behavior
* snapshot outputs match diff
* hash tests succeed
* no layer boundary violations (per SOP-100)
* storage ordering is stable
* code compiles and passes deterministic tests
* interaction with narrative follows the **Phase A / Phase I** contract

Only then is the SOT considered **“complete.”**