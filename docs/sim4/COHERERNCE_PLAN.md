# ✅ THE LOOPFORGE COHERENCE PLAN
_**(How we prevent duplication, drift, conflicts, and mismatched implementations)**_

The plan has **six pillars**.  
If we follow them, Loopforge stays rock-solid.

---

## 1. Canonical Sources of Truth (SOTs)
We define **four** SOT files that NOTHING else is allowed to contradict:

### SOT #1 — `ecs_spec.md`
Defines:
- what an entity is
- how components are stored
- what invariants exist
- what queries look like
- what safety guarantees exist
This governs the storage+query layer.

### SOT #2 — `agent_mind_spec.md`
Defines the 7-Level Mind, each with:
- conceptual purpose
- what components it owns
- what systems operate at that level
- what state transitions are allowed
- how it flows into the next layer
This governs the psychological architecture.

### SOT #3 — `brain_pipeline_spec.md`
Defines the update cycle:
```text
L1 Perception
L2 Emotion
L3 Cognition
L4 Intention
L5 Action
L6 Narrative
L7 Identity Drift
Resolution
```

Plus:
* input → output guarantees per phase
* determinism requirements
* ordering contracts
* what may and may not read/write
This governs systems.

### SOT #4 — `snapshot_spec.md`
Defines:
* how data flows from ECS to snapshots
* what Godot expects
* serialization rules
* stability rules
* how narrative and internal states are exposed
This governs the frontend.

---

## 2. Code Must Always Rebuild From SOTs
Every time we generate code, we explicitly reference:
* which SOT
* which section
* which definitions were used

That means:
> **🔒 We can never "accidentally redefine"**

because each file explicitly says:
```text
# Implements: agent_mind_spec.md §3.1 "Cognition Layer Components"
# Depends on: ecs_spec.md §2.3 "Component Storage"
# Provides: cognition_system() for brain_pipeline_spec.md §4.2
```

This is how human AAA studios do it (Frostbite, Snowdrop, UE Gameplay Tasks).

And LLMs are even better at this because they can follow breadcrumbs like a compiler.

---

## 3. Each Layer Has One Folder and One Responsibility

This eliminates duplicated logic.
```text
ecs/          → storage, queries, scheduler (never psychology)
components/   → data definitions only
systems/      → transformations of components
pipeline/     → execution order and coordination
agents/       → identity + starting bundles
snapshot/     → shaping and serialization only
```

🧠 Critical rule:
> **Components never contain logic**  
> **Systems never manage storage**  
> **Pipeline never mutates data directly**

This separation is how Unity DOTS and Bevy ECS avoid chaos.

---

## 4. The "Arbiter Model" for Avoiding Conflicts

This is the real secret sauce:  
> **🔵 Every level of the mind has an Arbiter**

A single file that defines the **valid state transitions**, for example:
* CognitionArbiter
* EmotionArbiter
* IntentionArbiter
* NarrativeArbiter
* PersonalityArbiter

They do not execute systems.  
They do **not** store data.

They define **rules** such as:
```text
If curiosity > 0.4 and confusion < 0.2, focusing is stable.
If tension > 1.2, intention may become freeze or avoid.
If arousal > 0.6, wandering is intensified.
```

> **Systems must obey them.**

**🎯 Why this prevents conflicts:**

Instead of systems inventing rules, they obey the Arbiter spec.

This keeps everything unified.

---

## 5. The “Registry Checkpoint” Mechanism

We maintain a single file:

`registry.py`

Which contains:
* registered components
* registered systems
* phase mapping
* snapshot field definitions
* narrative field mapping
Every time we add or modify something, we update the registry.

This allows:
* validation
* auto docs generation
* no drift
* no broken imports

---

## 6. Explicit Versioning of the Architecture (Era IV, V, VI)
At each major update, we produce:  
`eraV_upgrade_notes.md`

or similar.

This allows every next human or LLM Architect or Dev to know:
* what changed
* what stabilized
* what deprecated

We prevent divergent forks.

**🎯 With these six pillars, Loopforge cannot drift.**
Not even if you add:
* 20 new systems
* 15 agent archetypes
* 9 narrative layers
* full Godot visualization
* Rust backend next year

The codebase will remain coherent like an operating system.