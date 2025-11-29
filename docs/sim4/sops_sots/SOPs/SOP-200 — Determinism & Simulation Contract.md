# 🧭 SOP-200 — Determinism & Simulation Contract

Canonical Rules for the Tick Loop, State Mutation, and Reproducibility

(Draft 1 — Architect-Level, Long-Arc Compliant)

0. Purpose

Define exact rules for:

deterministic tick execution

allowed mutation pathways

event ordering

randomness handling

hashing and reproducibility

multi-engine compatibility (Python → Rust → GPU)

auditing, rollback, replay

This SOP is the physics contract of Loopforge.

Every system, component, and world interaction must obey it.

1. Deterministic Core Mandate

The simulation engine (Sim4+):

must produce identical outputs for identical inputs

given:

same initial WorldContext

same ECS state

same seed

same tick delta

same sequence of external inputs

No deviations are allowed.

All nondeterminism must be centralized, controlled, seeded, and logged.

2. Determinism Sources Threat List

Architect-GPT must explicitly guard against:

Python dict iteration order

iteration over unordered sets

floating-point nondeterminism

hidden random calls

OS scheduling

concurrency / async

time-based functions

hidden IO

global state

cross-layer calls

narrative interference

Python vs Rust differences

If any of these appear in SOTs or code → refuse or propose correction.

3. Tick Contract (Canonical Order)
   The simulation tick is a strict, ordered pipeline:
   tick(dt):
    1. Lock WorldContext
    2. Update Clock
    3. Phase A: Input Processing (deterministic ordering)
    4. Phase B: Perception
    5. Phase C: Cognition (non-LLM; deterministic)
    6. Phase D: Intention → ECS Commands
    7. Phase E: ECS Command Application (mutations occur here only)
    8. Phase F: World Updates (rooms, assets)
    9. Phase G: Event Consolidation
    10. Phase H: Diff Recording + History Append
    11. Phase I: Narrative Trigger (post-tick)
    12. Unlock WorldContext


ECS systems may run only inside Phases B–E.

Narrative must run only after Phase H, never earlier.

4. Allowed Mutation Points

Mutation may occur ONLY during:

✔ Phase E (ECS Mutation)

Through:

command buffers

deterministic entity creation/deletion

deterministic component writes

deterministic component updates

✔ Phase F (World Layer Updates)

room entry/exit

asset state updates

world events derived from ECS

✔ Phase H (History / Diff)

recording only

no state mutation

❌ Forbidden:

Mutation in any other phase.

Mutation inside narrative is forbidden.

Mutation inside snapshots is forbidden.

Mutation inside perception or cognition is forbidden.

5. Randomness Contract

Randomness is permitted only via the Simulation RNG service:

✔ Provided by runtime/engine
✔ Seeded by the scenario
✔ Logged per tick
✔ Deterministic cross-language (Python → Rust)

All randomness must be:

centralized

seeded

replayable

component-scoped or system-scoped, never global

❌ No system may use:

Python’s random

NumPy RNG

UUID

OS entropy

time-based randomness

If seen → Architect-GPT must refuse or replace.

6. Ordering Contract

All iteration over ECS or World structures must follow:

stable order

stable IDs

index-based order derived from storage

This ensures:

reproducible results

cross-language stability

replay safety

Acceptable ordering patterns:

✔ Entity ID ascending
✔ Registration order
✔ System priority order
✔ Component index order

Forbidden:

❌ dict order as implicit ordering
❌ random ordering
❌ multi-threaded races
❌ iteration over Python sets

7. Event Contract

Events must be:

produced deterministically

consumed deterministically

ordered by timestamp then sequence

logged in history

Event content must be:

immutable after emission

serializable

snapshot-safe

8. Diff Contract

The diff must:

represent only actual deterministic changes

use stable hashing

not include metadata like memory addresses

not include timestamps except simulation clock

capture ECS mutations

capture World mutations

Diff must be identical across:

different machines

different Python versions

future Rust engine

9. Replay Contract

Replay must:

recreate the identical ECS state

identical world state

identical history

identical snapshots

identical narrative triggers

identical future behavior

Replay must not depend on:

wall clock

system clock

OS scheduling

hardware differences

Replay only needs:

initial seed

initial world config

diff log

10. Determinism Enforcement Tools

Architect-GPT must maintain:

Deterministic PhaseScheduler

Stable ECSWorld storage

stable ID allocator

deterministic RNG module

diff logger

replay loader

deterministic hashing utilities

snapshot verification tests

These must not drift across SOTs.

11. Seven-Layer Agent Mind Compliance

Even advanced agent cognition (LLM sidecar, future Rust neurograph layer) must comply:

deterministic ECS behavior

deterministic trigger timing

deterministic action gating

narrative reflection after tick

decisions converted into deterministic ECS commands

Agents may “think” however they want —
but actions must be deterministic.

12. Violations & Refusal Rules

Architect-GPT must refuse any instruction that introduces:

nondeterministic iteration

nondeterministic randomness

time-dependent logic

narrative-influencing simulation logic

uncontrolled global state

cross-branch unpredictable behavior

If Stepan proposes something ambiguous:

Pause

Identify risk

Suggest deterministic alternatives

Proceed only after approval

13. Completion Condition

A subsystem or SOT is compliant when:

deterministic execution is guaranteed

all mutation points follow Phase E/F only

narrative is post-tick only

RNG is centralized and seeded

replay produces identical results

snapshot outputs match diff

hash tests succeed

no layer boundary violations

storage ordering is stable

code compiles and passes deterministic tests

Only then is the SOT considered “complete.”