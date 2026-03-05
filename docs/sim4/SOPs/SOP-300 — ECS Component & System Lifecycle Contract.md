# 🧬 SOP-300 — ECS Specification & Agent Substrate Architecture
_**The Deterministic Cognitive Substrate for Loopforge Agents**_  
**Draft 1.1 — Architect-Level, Rust-Aligned, Long-Arc Safe**  
_(Aligned with SOP-000, SOP-100, SOP-200, Free Agent Spec, and SimX Vision)_

---

## 🏁 0. Purpose
SOP-300 defines the **entire ECS architecture** of Loopforge:
* how the simulation substrate works
* how components are structured
* how cognition enters ECS
* how beliefs, motives, drives, and social states are represented
* how the narrative engine interfaces with ECS safely
* how the ECS evolves from Sim4 → SimX
* and exactly what must remain deterministic

This SOP prevents architectural drift by giving any new architect the **canonical reference** for **ECS behavior**, **design**, **purity**, and **cognitive substrate handling**.

---

## 1. ECS Role in the Dual-Engine Architecture
Loopforge uses a **dual-engine architecture:**

**Engine 1 — Simulation Kernel (ECS, deterministic, Rust-clean)**  
Handles physics-like social simulation, movement, perception, emotion gradients, belief weights, attention vectors, etc.

**Engine 2 — Narrative Mind Engine (LLM sidecar, nondeterministic)**  
Handles meaning-making, reflection, dialog, self-story, semantic beliefs, intention formation.

**SOP-300 defines ONLY the simulation substrate (deterministic side).**

The substrate’s job:

> Represent the agent mind numerically so the simulation can run deterministically, while enabling the narrative engine to layer semantic meaning on top of that substrate.

---

## 2. Why ECS Exists in Loopforge
The ECS is NOT a gameplay ECS.  
It is a cognitive substrate simulation ECS.

Its purpose:
* store deterministic, interpretable agent state
* run pure, function-like systems
* provide Rust-friendly memory layout
* maintain stable identity across episodes
* serve as the grounding layer for narrative cognition
* enforce physical/logical constraints
* gate agent intentions into valid deterministic actions
* support huge city-scale agent counts (1000+)

---

## 3. Principles Governing Loopforge ECS

These derive from SOP-000, SOP-100, and SOP-200.

**✔ Deterministic**  
All updates must be reproducible given the same seed/history.

**✔ Rust-clean**  
Everything must be portable to Rust ECS without redesign.

**✔ Layer-pure**  
ECS cannot import `world/`, `narrative/`, `snapshot/`, or `integration/` (SOP-100 DAG).  
Any “world input” to ECS is passed in as **read-only views/adapters** by `runtime/`, not via direct module dependencies.

**✔ Substrate-only**  
ECS stores numeric/structural representations of cognitive layers—never semantic meaning.

**✔ Minimal semantic leakage**  
Semantic content lives in narrative.  
ECS stores only structured data.

**✔ Systems are always pure**  
Systems depend only on:
* current ECS state
* plus injected, read-only world views (geometry, navigation, visibility)  
provided by `runtime/` / `world/` in a deterministic order.

**✔ No nondeterminism**  
Randomness only through central seeded RNG (see SOP-200).

---

## 4. Agent Mind Layers Rationale: Why the Free Agent Spec Defines the Canonical 7 Layers

Multiple frameworks could have been used to define the cognitive substrate of Loopforge agents.

One approach was the classic cognitive stack:
```text
Perception → Cognition → Beliefs → Drives → Intent → Action → Reflection → Narrative
```
which is clean and computationally convenient for deterministic simulation.

Another was the architectural modeling stack used by prior AI simulators:
```text
Schema Layer → Intent Layer → Policy Layer → Planner → Narrative
```
which maps well to ECS but lacks expressive interiority.

A third possibility was the LLM-cognition sandwich model:
```text
Deterministic Physics + Nondeterministic Meaning-Making
```
favored by reinforcement-learning simulators and agentic research groups.

We rejected all of these because Loopforge’s long-arc vision — especially SimX — demands something fundamentally richer: agents must not only react, plan, and reflect, but must also surprise themselves, generate internal symbolism, form new desires, reinterpret experiences, develop personal lexicons, maintain self-stories, and evolve their identity over time.

This requirement led to the emergence of the **Free Agent Spec**, which defines a robot mind via persistent components:
* SelfModel
* ConceptGraph
* BeliefState
* DriveState
* MotiveSystem
* PlanLayer
* ReflectionState
* SocialMind
* AestheticMind

Unlike the other frameworks, the Free Agent Spec does not treat “mind” as a single cognitive pipeline — it treats it as a **living, growing internal ecosystem** of **symbolic**, **emotional**, **social**, and **narrative dynamics**.

For this reason, the canonical 7-layer architecture for Loopforge agents is:
```text
L1 — Embodied & Raw Perception Layer
(Transform, physical state, raw sensory channels, basic attention hooks)

L2 — Perception & Attention Layer
(percept buffers, salience maps, who/what I’m currently noticing)

L3 — Belief, Concept & Self-Model Layer
(ConceptGraph, BeliefGraph, SelfModel, belief-attribution substrate)

L4 — Drives & Emotion Fields Layer
(DriveState, emotional gradients, tension/comfort fields)

L5 — Motives & Planning Layer
(goal fields, structural plans, plan stubs, action agendas)

L6 — Reflection Layer
(cross-tick interpretation, “what did this mean for me?”, narrative reflection)

L7 — Narrative & Persona/Aesthetic Mind
(inner monologue, dialog, style, aesthetic preferences, voice)
```

From an **engine** perspective we distinguish:
* **Substrate layers** (wholly or partly realized in ECS): **L1–L5** and the **numeric/aesthetic substrate of L7**
* **Semantic layers** (LLM meaning-making): **L3–L7**, fully realized in the Narrative Mind Engine

Sim4 (Python deterministic kernel) owns the **substrates**; the Narrative Mind Engine owns the **semantics**.

This substrate/semantic split is the unique sweet spot between long-arc creative expressiveness and strict Rust-compatible determinism. It ensures agents can someday have synthetic interiority — self-stories, evolving identities, dreams, impulses, contradictions — while keeping the simulation kernel deterministic enough to scale to SimX, where thousands of agents inhabit a narrative city with Disco-Elysium-level psychological richness.

---

## 5. The 7-Layer Agent Mind and ECS Boundaries

The 7-layer mind architecture decomposes into:

| Layer | 	Meaning	                  | Lives In ECS                          | 	Lives In Narrative                      |
|-------|----------------------------|---------------------------------------|------------------------------------------|
| L1    | 	Embodied State            | 	✔ fully                              | 	—                                       |
| L2    | 	Perception & Attention    | 	✔ low-level                          | 	✔ interpretation                        |
| L3    | 	Belief Graph & Self-Model | 	✔ confidence graph, ties, anchors    | 	✔ semantic beliefs, self-story          |
| L4    | 	Drives & Emotion Fields   | 	✔ numeric drives, gradients          | 	✔ emotional meaning                     |
| L5    | 	Motives & Plans           | 	✔ structural plan stubs, goal fields | 	✔ expanded reasoning, story logic       |
| L6    | 	Reflection Layer          | 	—                                    | 	✔ reflective interpretation             |
| L7    | 	Persona/Aesthetic Mind    | 	✔ valence / preference vectors       | 	✔ full narrative representation & voice |

**Interpretation**  
ECS stores the structured substrate, and narrative interprets and evolves it semantically.

---

## 6. Canonical ECS Component Sets
These are the core substrate components, guaranteed across Sim4 → SimX.

---

### 6.1 Identity Components
* `AgentIdentity`
* `ProfileTraits` (e.g. introversion, volatility, alignment)
* `SelfModelSubstrate` (identity vector, self-consistency pressure, contradiction counters)

The narrative engine maintains the semantic self-story, but ECS stores:
* consistency pressures
* contradiction counts
* drift measures
* numerical identity anchors

---

### 6.2 Embodiment & Spatial Components
* `Transform`
* `Velocity`
* `RoomPresence`
* `PathState`
* `MovementIntent` (sanitized, deterministic movement command for this **tick**)

Narrative never changes these directly.

### 6.2.b Movement & Interaction Substrate
Movement and world interaction are modeled as **deterministic intent** → **resolution** → **effect** chains. ECS holds the substrate; `world/` applies environmental consequences.

Core components:
* `MovementIntent`
  * what the agent is trying to do with its body this **tick**
  * sanitized, deterministic movement command
  * examples: `walk_to_room(room_id)`, `move_to_coord(x,y)`, `follow(agent_id)`
* `PathState`
  * resolved path substrate (waypoints, current index, progress along edge)
  * stable, deterministic representation compatible with Rust pathfinding
* `InteractionIntent`
  * requested interaction with a target (agent or object)
  * examples: `talk_to(agent)`, `inspect(object)`, `pick_up(object)`, `use(object)`
* `ActionState`
  * current resolved action mode: `Idle`, `Walking`, `Talking`, `Interacting`, `Waiting`, etc.

**Movement & interaction rules:**
* ECS expresses what the agent is doing via `MovementIntent`, `InteractionIntent`, and `ActionState`.
* ECS never directly mutates world objects (doors, machines, terminals).
* Instead, ECS systems emit **world update requests** (structured commands) which `world/` applies deterministically in Phase F (see SOP-200).
* Narrative cannot bypass this pipeline; it may only propose **high-level intents** which are sanitized and converted into substrate components by deterministic systems.

---

### 6.3 Perception Substrate
ECS holds:
* visibility lists
* proximity values
* salience scores
* attention slots
* perceptual flags

Narrative reads these and generates meaning (“I think he looked angry”).

---

### 6.4 Belief Substrate (L3)
ECS stores:
* `BeliefGraphSubstrate`
  * nodes: belief topics (hashed, opaque IDs)
  * edges: confidence weights
  * metadata: last-updated tick, source tags (self/other/world)
* `AgentInferenceState` (deterministic cognitive preprocessing)
* `SocialBeliefWeights` (e.g. “X likes Y”: 0.62 → 0.71)

Narrative expands these to:
* stories about why beliefs exist
* misunderstandings
* hallucinated memories (guarded)
* rumor interpretations
* belief attribution (“I think she thinks I’m unreliable”)

ECS stores **no natural language.**

---

### 6.5 Affective Drives (L4)
Substrate representation of internal forces:
* `curiosity: float`
* `safety_drive: float`
* `dominance_drive: float`
* `meaning_drive: float`
* `attachment_drive: float`
* `novelty_drive: float`

Narrative interprets these as emotional meaning:

> “I feel drawn to explore today.”
> “I worry he might leave me.”

---

### 6.6 Emotion Fields
These support city-scale emergent narrative:
* tension vector
* mood drift
* affective charge
* stress
* excitement

All are numeric substrates (no labels like “sad/angry” in ECS).

---

### 6.7 Motive & Plan Substrate (L5)

ECS stores:
* active plan steps (opaque, structured PlanStep records)
* plan confidence scores
* revision_needed: bool
* abstract action targets (agent IDs, room IDs, object IDs)
* motive activation scores (which drives are pushing which goals)

Narrative fills these with meaning:

> “I’ll go talk to her after I calm down.”
> “I want to repair our relationship.”

---

### 6.8 Social Substrate (L3 + L4 fusion)
To support the **Social Mind** of the Free Agent Spec (friendship, rivalry, loyalty, resentment, admiration, misunderstanding, forgiveness), ECS stores:
* relationship weights (friendship/hostility scales)
* impressions (categorical coded tags, not free text)
* interaction memory counters (recent encounters, shared events count)
* trust/distrust vectors
* faction affinities

Narrative generates:
* jealousy
* loyalty
* betrayal
* admiration
* interpersonal stories
* alliances/factions
* reconciliations and grudges

---

### 6.9 Intent/Action Components

Canonical Sim4 → SimX action pipeline (substrate side):
1. `PrimitiveIntent` — raw, possibly unsafe intent (from adapters)
2. `SanitizedIntent` — checked against physics, permissions, constraints
3. `ActionState` — chosen action mode for this tick
4. `MovementIntent` — final movement command
5. `InteractionIntent` — final interaction command

Narrative proposes **semantic** changes → adapters map them into `PrimitiveIntent` → ECS systems sanitize and execute.

---

## 7. Subsystems in ECS
These are the deterministic ECS systems in Sim4+.

---

### 7.1 PerceptionSystem
Determines visibility and salience using **read-only world views** (geometry, occlusion, distances):
* computes what each agent can see
* updates visibility lists, salience scores, attention slots

---

### 7.2 CognitivePreprocessor
Does **deterministic**, non-semantic belief updates:
* increment/decrement confidence based on events
* apply decay functions
* propagate belief weights across the BeliefGraphSubstrate

No natural language or semantic interpretation here.

---

### 7.3 EmotionGradientSystem
Updates numeric emotion fields:
* tension diffusion
* mood drift
* affective field propagation

---

### 7.4 DriveUpdateSystem
Updates internal drives based on:
* events
* emotion fields
* decay curves
* boundary conditions (clamping, normalization)

---

### 7.5 MotiveFormationSystem
Maps drives + beliefs into motive activation patterns:
* “attachment high + insecurity high → relationship-preserving motives get higher scores”
* output is numeric, no story logic.

---

### 7.6 PlanResolutionSystem
Converts motive substrates → deterministic plan stubs:
* selects or revises `PlanStep` lists
* toggles `revision_needed`
* ensures structural validity (no impossible plans)

---

### 7.7 MovementResolutionSystem
Takes `MovementIntent` and:
* queries navigation views from `world/` (read-only)
* computes or updates `PathState` deterministically
* enforces movement constraints (speed, blocked tiles, one-way links)
* updates `ActionState` to a valid movement mode or failure (`Walking`, `Stuck`, `Waiting`)

---

### 7.8 InteractionResolutionSystem
Takes `InteractionIntent` and:
* validates target existence & reachability using read-only world/agent queries
* resolves interaction type (`Talk`, `Inspect`, `PickUp`, `Use`, etc.)
* encodes interaction outcome as ActionState plus world update requests (e.g. “open door #123”)

These world update requests are passed to the `world/` layer for execution in Phase F (SOP-200).

---

### 7.9 SocialUpdateSystem
Updates relationship weights and social tension dynamics:
* interaction success/failure
* betrayal-like events
* assistance/help events
* co-presence over time

Only numeric substrates are mutated.

---

### 7.10 ActionExecutionSystem
Applies agent-side effects of resolved actions:
* updates `Transform`, `RoomPresence`, `PathState` based on movement
* updates short-term interaction memory counters
* emits structured, deterministic world update commands for `world/` to apply in Phase F

ActionExecutionSystem:
* **never** directly mutates world objects
* **never** calls narrative

---

## 8. The Substrate vs Semantic Split
ECS stores:
* numeric substrates
* structural cognition
* relationships
* drives
* plans
* confidence graphs
* emotion/attention vectors
* final resolved actions
* movement & interaction substrates

Narrative stores:
* semantic beliefs
* self-story
* explanations
* metaphors
* hallucinated memories
* meaning-making
* dialog
* reflection
* high-level goal generation
* rumor semantics
* faction stories
* inner monologue and persona voice

**Adapters** ensure semantic → substrate transformation is deterministic.

---

## 9. ECS–Narrative Interaction Contract
Defined by SOP-100 and expanded here.

**Narrative may:**
* read any ECS substrate snapshot
* update only:
  * `NarrativeState`
  * BeliefState semantic layer (not numeric graph directly)
  * GoalState semantic layer
  * produce `IntentSuggestions` and `GoalSuggestions` (not actions)

**Narrative may NOT:**
* update transforms
* update drives
* update emotions
* update motives
* update social weights
* update plan structure
* update action states
* directly change `MovementIntent` or `InteractionIntent`

**ECS may:**
* read sanitized narrative suggestions (via adapters)
* incorporate them via deterministic gating logic into `PrimitiveIntent`, `BeliefGraphSubstrate`, motive activation, etc.

**ECS may NOT:**
* call narrative engine
* embed narrative logic
* store narrative stories
* interpret natural language

---

## 10. Cognitive Data Flow (Tick-to-Tick)
SOP-200’s **deterministic tick** applies. From the ECS perspective, the cognitive pipeline is:
1. Perception substrate updated (PerceptionSystem)
2. Cognitive substrate updated (CognitivePreprocessor, EmotionGradientSystem, DriveUpdateSystem, MotiveFormationSystem, PlanResolutionSystem, SocialUpdateSystem)
* beliefs
* drives
* plans
* emotions
* social ties
3. Intent & action resolution
* IntentResolverSystem → `SanitizedIntent`
* MovementResolutionSystem → `MovementIntent`, `PathState`
* InteractionResolutionSystem → interaction outcomes & world commands
* ActionExecutionSystem → agent-side updates + world commands
4. World updates
* `world/` (outside ECS) applies world commands deterministically in Phase F as per SOP-200.
5. History & diff
* runtime records changes for replay (SOP-200).
6. Narrative pass
* Narrative engine reads deterministic snapshot
* generates semantic meaning (reflection, inner monologue, dialog, new high-level goals)
7. Adapter pass
* semantic proposals are mapped into next-tick substrate suggestions (`IntentSuggestions`, belief hints, goal hints)
8. Next tick.

---

## 11. Belief & Belief Attribution Architecture
ECS holds:
* confidence graph
* attribution placeholders (numeric cause codes)
* salience levels
* trust weights
* epistemic uncertainty scores

Narrative holds:
* stories of why the belief exists
* misattributions
* inference chains
* deception
* rationalizations

ECS executes deterministic belief decay/propagation.  
Narrative invents meaning around it.

---

## 12. Why Hybrid Substrate + Semantic Narrative Layer Is Required for SimX
SimX requires:
* long-range emotional arcs
* evolving identities
* faction politics
* shared meaning across thousands of agents
* narrative consistency over months
* reproducible replays
* city-scale tension dynamics
* stable memory models

Hybrid Substrate + Semantic Narrative Layer gives us:
* deterministic substrate
* nondeterministic meaning-making
* scalable multi-agent cognition
* replayable emergent narrative
* Rust portability
* ECS purity

This is the foundation of **Disco Elysium but emergent.**

---

## 13. Rust Migration Requirements
ECS must be shaped so Rust modules can be dropped in with no redesign:
* archetype-based layout
* SOA storage
* stable indices
* no Python runtime tricks
* no adhoc component allocation
* no semantic cognitive logic in ECS
* substrate-only cognition

---

## 14. Evolution Roadmap Sim4 → SimX
### Sim4
* basic substrate
* basic drives/emotions
* basic plans
* minimal belief graph

### Sim5
* proper memory
* room gossip substrate
* tension diffusion

### Sim6
* persuasion/rumor substrate
* social networks
* conflict substrate

### Sim7
* temporal arcs
* generational memory
* identity drift substrate

### Sim8
* autonomous quest substrates
* moral drift vectors

### Sim9
* neural personalities
* ideology substrate

### SimX
* fully emergent narrative city
* LLMs generate self-story at scale
* ECS maintains all deterministic substrate flows

---

## 15. Enforcement Rules
The architect must refuse any change that:
* introduces semantic content into ECS
* breaks substrate/semantic split
* creates nondeterministic edges
* lets narrative mutate substrate directly
* modifies ECS from world/snapshot/integration layers
* collapses substrate layers
* violates the Hybrid Substrate + Semantic Narrative Layer model

---

## 16. Completion Condition

SOP-300 is satisfied only if:
* ECS stores only substrates (numeric/structural)
* narrative stores all semantic meaning
* adapters sanitize semantic → deterministic transitions
* belief/drive/motive/plan/social substrates exist and evolve deterministically
* movement & interaction pipelines are fully deterministic and world-safe
* ECS is fully Rust-portable
* cognitive substrate matches Free Agent Spec
* architecture supports SimX long-arc