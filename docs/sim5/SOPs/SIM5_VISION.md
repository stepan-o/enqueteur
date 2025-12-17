# 🌆 LOOPFORGE ERA 5 — SIM5
## _Deterministic City Kernel + Protocol-Native Viewers_

_Draft v1.0 — STEPAN_LEVEL +30_

---

## 📌 Executive Summary

**Sim5** is the first **platform-grade** Loopforge engine.

It is no longer “a simulation that happens to have a viewer.”
It is a **deterministic city kernel** that speaks a public protocol
and can be rendered, replayed, and distributed across:

- Godot
- Unreal Engine (5.7+)
- Unity
- UEFN / Fortnite-style experience shells (future)

Sim5 is where Loopforge **joins the party** —
not as another engine, but as the **engine beneath engines**.
## 🧠 Core Shift from Sim4 → Sim5

Sim4 proved:
- deterministic ticks
- ECS cleanliness
- diff-based viewer state
- early narrative hooks

Sim5 formalizes:
- **Kernel ↔ Viewer as protocol**
- **Replay as a first-class citizen**
- **Engines as replaceable shells**
- **Distribution-readiness**

> If Sim4 was a prototype,
> **Sim5 is a public interface with a soul.**
## 🎯 Sim5 Design Goals

Sim5 must:

1. Run headless and deterministically
2. Stream state exclusively via KVP-0001
3. Support live play AND replay with identical semantics
4. Allow multiple simultaneous viewers
5. Treat Unreal / Unity / Godot as equal citizens
6. Preserve narrative emergence without breaking determinism
7. Scale forward to SimX without architectural rewrites
## 🧱 Architectural Principle: The Kernel Is the Product

Sim5 is composed of **three strictly separated planes**:

1. **Simulation Kernel** (authoritative, deterministic)
2. **Narrative Sidecar** (non-deterministic, asynchronous)
3. **Viewer Layer** (external, engine-specific)

Only ONE direction of authority exists:

Viewer → Command → Kernel → Snapshot/Diff → Viewer
## 🧠 1. Simulation Kernel (Sim5 Core)

The kernel is:

- deterministic
- replayable
- headless
- engine-agnostic

Responsibilities:
- ECS execution
- tick scheduling
- spatial simulation
- world events
- social state updates
- emotional field propagation
- history + diff generation

The kernel **never**:
- renders
- runs LLMs
- generates dialogue
- makes aesthetic decisions
## ⚙️ 1.1 Determinism Contract

Sim5 guarantees:

(seed, initial_state, command_log) → identical future

This is enforced by:
- fixed tick rate
- ordered system execution
- quantized floats
- canonicalized output
- step_hash per tick

Determinism is not an optimization.
It is **constitutional law**.
## 🧬 1.2 Kernel Output: KVP-0001

The kernel emits **only**:

- FULL_SNAPSHOT
- FRAME_DIFF

Both are:
- primitives-only
- schema-versioned
- canonicalized
- stable-ordered

There is no other way to observe the world.
## 🖥️ 2. Viewer Layer (External Engines)

A viewer is **any engine** that implements KVP-0001.

Examples:
- Godot (2.5D isometric, Disco vibe)
- Unreal Engine 5.7 (cinematic, volumetric, AAA)
- Unity (tooling-heavy, editor-first)
- Future: UEFN shells

Viewers:
- do NOT simulate
- do NOT store authoritative state
- do NOT invent outcomes
## 🖼️ 2.1 Viewer Responsibilities

A viewer must:
- connect via KVP-0001
- request snapshot
- apply diffs in order
- visualize agents, rooms, events
- display narrative fragments
- emit INPUT_COMMAND messages

A viewer may:
- interpolate visuals
- animate transitions
- stylize presentation
- add UI affordances

A viewer must never:
- change simulation outcomes
## 🎮 2.2 Input Philosophy: Indirect Control

Sim5 does NOT support:
- direct avatar control
- god-mode editing
- imperative scripting

Instead, viewers send:
- WORLD_NUDGE commands
- DEBUG_PROBE requests
- REPLAY_CONTROL signals

Players influence the world
**like weather, not hands**.
## 🧠 3. Narrative Sidecar (Mind Engine)

Narrative is **not part of the kernel**.

The sidecar:
- receives perception logs
- receives emotional gradients
- receives social changes
- generates meaning

Outputs:
- dialogue
- inner monologue
- belief updates
- goal suggestions

These outputs are:
- advisory
- tagged non-deterministic
- never used as kernel inputs directly
## 🗣️ 3.1 Narrative Projection Rules

Narrative fragments may be:
1. Kernel-derived summaries (deterministic)
2. Sidecar-generated reflections (non-deterministic)

All narrative fragments:
- are viewer-facing only
- have TTL
- are replaceable
- do not affect physics, memory, or causality
## 🧩 4. World Model (City-Scale)

Sim5 world is:
- multi-room
- multi-zone
- graph-connected
- time-aware

Supports:
- streets
- interiors
- plazas
- districts
- ambient systems

World state includes:
- occupancy
- tension
- temperature
- ambient noise
- social density
## 🌡️ 4.1 Emotional & Social Fields (New in Sim5)

Sim5 introduces **continuous fields**:

- emotional tension
- curiosity density
- hostility gradients
- gossip pressure

These are:
- numeric
- spatially distributed
- updated per tick
- visible to viewers as overlays

Fields drive emergence.
## 🧠 5. Agents (Pre-Free-Agent Phase)

Sim5 agents are:
- embodied
- socially reactive
- emotionally dynamic

They have:
- EmotionalState
- SocialState
- IntentState
- ActionState
- MemoryTrace (raw)

They do NOT yet:
- self-generate long arcs
- hold ideology
- create autonomous quests

That is Sim6+ territory.
## 🔁 6. Replay Is First-Class

Every Sim5 run supports:
- full replay
- seek
- scrub
- multi-viewer playback

Replay uses:
- identical snapshots
- identical diffs
- identical commands

Replay is not a recording.
It is **time travel**.
## 🧪 7. Testing & Verification

Sim5 requires:
- golden snapshot fixtures
- golden diff streams
- step_hash verification
- viewer desync detection

CI must prove:
- deterministic parity
- schema stability
- replay fidelity

If it can’t be replayed,
it didn’t happen.
## 🚀 8. Why Sim5 “Joins the Party”

Unreal 5.7, Unity, and Fortnite are converging
toward **interoperable runtime shells**.

Sim5 is already there.

Loopforge does not compete with engines.
It **feeds them meaning**.

> Engines render worlds.
> Loopforge grows civilizations.
markdown
Copy code
## 🏁 Closing

Sim5 is the first Loopforge engine
that can survive outside its own lab.

It is:
- portable
- replayable
- cinematic
- distributable
- future-proof

Sim5 is where Loopforge stops being “a project”
and becomes **infrastructure for synthetic life**.