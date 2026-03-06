This is the **fully updated, complete feature spec** with the Phase 0 closure items integrated, without dropping any prior locked content.

---

# Enquêteur v1.0 — Feature Spec

## Case 1: **MBAM — Le Petit Vol du Musée**

### Tagline

**“Un petit objet. Un grand embarras.”**

---

# 0) Purpose of This Spec

This document is the canonical implementation spec for **Enquêteur v1.0**.

It exists to:

* lock scope
* prevent platform drift
* define the first playable target
* define truth ownership boundaries
* freeze the MBAM content scope
* freeze the core data contracts
* define the execution order
* define the first implementation task

This spec is intended to conclude **Phase 0** and make the project ready for implementation.

---

# 1) Core Product Definition

## Enquêteur v1.0 is:

A **single fully playable deterministic investigation case vertical slice** built on top of the current cleaned Sim4-based repo.

It is:

* one case
* one location set
* one recurring cast
* one complete investigation loop
* deterministic and replayable
* French-learning-oriented
* playable without a live LLM
* designed so a later LLM can act only as a dialogue surface adapter

## Enquêteur v1.0 is **not**:

* a generalized investigation platform
* a multi-case narrative engine
* a generalized content authoring framework
* a production voice-first system
* a fully autonomous LLM mystery simulator
* a generalized minigame framework
* a generalized social simulation sandbox

This is a **case-first implementation**, not a platform-first implementation.

---

# 2) Scope Lock — What Must Ship in v1.0

## Required for Enquêteur v1.0

* one case: **MBAM / Le Petit Vol du Musée**
* one fixed location set
* one fixed recurring cast of five characters
* three deterministic seeds: **A / B / C**
* deterministic case truth
* object-based investigation
* evidence and contradiction logic
* structured French dialogue interactions
* narrow A1–A2 scaffolding
* four MBAM-specific minigames
* one accusation/recovery resolution loop
* soft-fail support
* offline replay/debug support
* deterministic end-to-end reproducibility for shipped seeds

## Explicitly not required for initial ship

* generalized multi-case framework
* generic content pipelines beyond MBAM needs
* live websocket-first runtime as the main path
* production voice input/output
* fully dynamic LLM-owned dialogue
* generalized inventory framework
* generalized clue-board framework beyond what MBAM requires
* generalized minigame system beyond MG1–MG4
* production-quality art pipeline automation
* fully generalized pathfinding/social-sim expansion unless MBAM directly needs it

---

# 3) Architecture Lock — Truth Separation

Enquêteur uses **three strictly separated truth layers**.

## Layer A — World Truth

Owned by the **Sim4 runtime**.

World Truth includes:

* rooms
* doors
* objects
* item locations
* agent positions
* room access
* world clock
* movement
* world mutations
* visibility / reachability / availability

## Layer B — Case Truth

Owned by the **deterministic MBAM Case Bundle**.

Case Truth includes:

* culprit
* ally
* misdirector
* method
* drop location
* motive
* cast overlays
* evidence placement
* alibi matrix
* truth graph
* contradiction graph
* timeline beats
* scene gates
* resolution rules
* success / fail / best-outcome conditions
* visible/hidden fact slices

## Layer C — Dialogue / Pedagogy Adapter

Owned by the **dialogue and scaffolding layer**.

This layer includes:

* player input interpretation
* legal response selection
* allowed-fact presentation
* sentence stems
* hint tiers
* repair/rephrase behavior
* summary checks
* French difficulty tuning
* state-card presentation hints
* optional future voice hooks

## Hard rules

* **Case Truth is canonical for all non-physical gameplay logic.**
* **World Truth must not secretly own mystery truth.**
* **Dialogue layer may adapt wording and pacing, but may never invent or alter core case truth.**
* No core mystery truth may exist only in:

    * frontend UI state
    * ad hoc NPC runtime memory
    * object-local behavior alone
    * LLM output

---

# 4) Design Goals

* **A1–A2 playable** on first run.
* **Replayable** through deterministic seeded variation.
* **Living-world feel** through visible movement, room presence, and timing pressure.
* **Recurring cast** with stable identities and variable seeded overlays.
* **Deterministic solvability** in every shipped seed.
* **LLM-safe architecture** where future dialogue naturalness does not compromise truth control.
* **Pixi-friendly scope** with readable geometry and prop-based clue interactions.
* **Offline replay/debug priority** over live runtime polish in the initial build.
* **Voice-ready boundary**, but not voice-required for initial implementation.

---

# 5) Canonical Content Scope Freeze

The following content is frozen for MBAM v1.0 and should be treated as source-of-truth content scope.

## Rooms

1. **MBAM Lobby**
2. **Gallery 1 — Salle des Affiches**
3. **Security Office**
4. **Service Corridor**
5. **Café de la Rue**

## Fixed cast

* **Élodie Marchand** — Curator
* **Marc Dutil** — Guard
* **Samira B.** — Intern
* **Laurent Vachon** — Donor/VIP
* **Jo Leclerc** — Barista/Witness

## Objects

* O1 Display Case / Vitrine
* O2 Le Médaillon
* O3 Wall Label / Cartel
* O4 Bench
* O5 Visitor Logbook
* O6 Badge Access Terminal
* O7 Security Binder
* O8 Keypad Door
* O9 Receipt Printer / Café Receipts
* O10 Bulletin Board

## Evidence items

* E1 Torn Note
* E2 Café Receipt
* E3 Lanyard Fiber / Sticker

## Structured scenes

* S1 Lobby Intro
* S2 Security Gate
* S3 Timeline Witnessing
* S4 Café Witness
* S5 Confrontation / Recovery

## Minigames

* MG1 Label Reading
* MG2 Badge Log Read
* MG3 Receipt Reading
* MG4 Torn Note Reconstruction

## Timeline beats

* T+00 arrival / medallion missing
* T+02 curator containment
* T+05 guard patrol
* T+08 intern movement beat
* T+10 donor arrival/call
* T+12 witness window strongest
* T+15 terminal archival / increased friction

## Seeds

* Seed A
* Seed B
* Seed C

## Success/fail requirements

* one recovery success path
* one accusation/reasoning success path
* one soft-fail branch per shipped seed

---

# 6) World Layout (Pixi-Friendly)

Represent the case world as simple readable rooms using Sim4-compatible geometry.

## Rooms

1. **MBAM Lobby** — public
2. **Gallery 1 — Salle des Affiches** — semi-public
3. **Security Office** — restricted
4. **Service Corridor** — restricted
5. **Café de la Rue** — public

## Connections / gates

* Lobby ↔ Gallery 1: open
* Lobby ↔ Security Office: restricted; requires permission / escort / trust gate
* Gallery 1 ↔ Service Corridor: restricted; guard-controlled
* Lobby ↔ Café: open

## Visual prop goals

Minimal, readable, mostly static:

* **Lobby**: reception desk, coat rack, brochure stand, scanner
* **Gallery**: vitrine, wall label, bench, camera dome
* **Security Office**: terminal, binder, lanyards, radio dock
* **Corridor**: cart, bin, keypad door
* **Café**: counter, receipt printer, board, queue markers

---

# 7) MBAM Case Bundle (Canonical Case Truth)

The **MBAM Case Bundle** is the canonical non-physical gameplay object.

## Inputs

* `case_id = MBAM_01`
* `seed`
* `difficulty_profile`
* `runtime_clock_start`

## Outputs

* `cast_overlay`
* `roles_assignment`
* `timeline_schedule`
* `evidence_placement`
* `alibi_matrix`
* `truth_graph`
* `scene_gates`
* `resolution_rules`
* `visible_case_slice`
* `hidden_case_slice`

## Role slots

* `CULPRIT ∈ {Intern, Donor, Outsider}`
* `ALLY ∈ {Guard, Barista, Curator}`
* `MISDIRECTOR ∈ {Curator, Intern, Donor}`
* `METHOD ∈ {badge_borrow, case_left_unlatched, delivery_cart_swap}`
* `DROP ∈ {café bathroom stash, corridor bin, coat rack pocket}`

## Hard rule

Everything needed to answer:

* who did it
* how
* when
* what evidence proves it
* what contradictions matter
* what endings are legal

must come from this bundle.

---

# 8) Cast Registry (Persistent Recurring Characters)

The five MBAM characters are a **persistent cast layer**, not throwaway NPCs.

## Élodie Marchand — Curator

* identity: curator
* baseline traits: proud, precise, impatient with vagueness
* baseline speech: formal French
* tell pattern: insists on exact wording and exact time
* trust trigger: polite register, accurate summaries
* anti-trigger: sloppy accusations

## Marc Dutil — Guard

* identity: security guard
* baseline traits: procedural, tired, rule-bound
* baseline speech: short, direct, protocol-focused
* tell pattern: hides behind process
* trust trigger: competence + respectful tone
* anti-trigger: trying to skip procedure

## Samira B. — Intern

* identity: intern
* baseline traits: anxious, eager, oversharing
* baseline speech: simpler French, some anglicisms
* tell pattern: too many details when nervous
* trust trigger: reassurance, calm pacing
* anti-trigger: direct pressure too early

## Laurent Vachon — Donor/VIP

* identity: donor/VIP
* baseline traits: polished, status-aware, defensive
* baseline speech: polished French, may code-switch to English if irritated
* tell pattern: avoids exact times
* trust trigger: formal address, tact
* anti-trigger: perceived disrespect

## Jo Leclerc — Barista/Witness

* identity: barista/witness
* baseline traits: observant, casual, social
* baseline speech: Montreal casual French, idioms scaled by difficulty
* tell pattern: remembers vibe/clothes before names
* trust trigger: friendliness, specificity
* anti-trigger: stiff interrogation tone

## Cast overlay model

Each run applies a seeded overlay that controls:

* role in this case
* helpfulness
* what they know
* what they believe
* what they hide
* what they misremember
* state-card display profile

---

# 9) State Cards / Portrait Hint System

State cards are a **core gameplay hint system**, not decorative UI.

Each major dialogue turn may display:

* portrait/state art variant
* emotional state
* stance
* soft alignment hint
* trust trend
* tell cue
* suggested interaction mode

## Emotion values

* calm
* stressed
* amused
* annoyed
* nervous
* guarded

## Stance values

* helpful
* procedural
* evasive
* defensive
* manipulative
* flustered

## Soft alignment hint values

* protecting institution
* protecting self
* protecting someone else
* trying to save face
* trying to help quietly

## Gameplay use

State cards hint:

* which tone to use
* whether to ask directly or indirectly
* whether to use `vous`
* whether contradiction pressure is safe
* whether the NPC’s discomfort suggests guilt, fear, embarrassment, or loyalty

---

# 10) World Objects + MBAM-Specific Affordances

Objects are implemented case-first. Generalization can happen later.

## O1 — Display Case (Vitrine)

### State

* `locked|unlocked`
* `contains_item:boolean`
* `tampered:boolean`
* `latch_condition`

### Affordances

* `inspect()`
* `check_lock()`
* `examine_surface()`

### Case use

* establishes missing item
* may reveal method clue
* supports early suspicion

## O2 — Missing Item: Le Médaillon

### State

* `present|missing|recovered`
* `location`
* `examined:boolean`

### Affordance

* `examine()`

### Case use

* provides confirmation detail or inscription clue after recovery

## O3 — Wall Label (Cartel)

### State

* `text_variant_id`

### Affordance

* `read()`

### Case use

* **MG1**
* extracts title/date
* acts as French reading interaction

## O4 — Bench

### State

* `under_bench_item:boolean`

### Affordance

* `inspect()`

### Case use

* may reveal torn note fragment or dropped paper

## O5 — Visitor Logbook

### State

* entries list
* scribble pattern

### Affordance

* `read()`

### Case use

* supports presence reasoning
* provides mild role/context clue

## O6 — Badge Access Terminal

### State

* `online:boolean`
* `log_entries:[{badge_id, time, door}]`
* `archived:boolean`

### Affordances

* `request_access()`
* `view_logs()`

### Case use

* **MG2**
* timeline contradiction evidence
* pressure window before archival

## O7 — Security Binder

### State

* `page_state`

### Affordance

* `read()`

### Case use

* reveals procedure rule
* helps restore access path if terminal gate was missed

## O8 — Keypad Door

### State

* `locked`
* `code_hint`

### Affordances

* `inspect()`
* `attempt_code()` (optional branch)

### Case use

* reinforces access restrictions

## O9 — Receipt Printer / Café Receipts

### State

* `recent_receipts:[{time, item}]`

### Affordances

* `ask_for_receipt()`
* `read_receipt()`

### Case use

* **MG3**
* supports/refutes alibi timing

## O10 — Bulletin Board

### State

* flyer text

### Affordance

* `read()`

### Case use

* optional vocab reward / world texture

## Evidence items

### E1 — Torn Note

* `reconstruct()`
* **MG4**
* yields meeting/drop clue

### E2 — Café Receipt

* inventory evidence item
* used in contradiction or alibi challenge

### E3 — Lanyard Fiber / Sticker

* environmental evidence
* tied to cart/badge-related method

---

# 11) Timeline Structure (Real-Time, Deterministic, Branchy)

The world clock runs continuously, but case beats are deterministic.

## Baseline beats

* **T+00** player arrives; medallion already missing
* **T+02** curator begins containment mode
* **T+05** guard patrol / position change
* **T+08** intern transitions rooms
* **T+10** donor appears or calls
* **T+12** barista witness window is strongest
* **T+15** terminal log archival / increased access friction

## Time-pressure rules

* waiting changes witness quality
* waiting can reduce evidence visibility
* waiting can move NPCs
* early confrontation with weak evidence reduces trust
* missed clue windows remain recoverable through alternate paths, but harder

## v1.0 rule

Every shipped seed must remain solvable even if the player misses the optimal timing path.

---

# 12) Evidence + Contradiction Graph

This is part of **Case Truth**, not a UI convenience layer.

## Primary clue types

1. access clue
2. time clue
3. text clue
4. contradiction clue
5. location clue

## Minimum viable nodes

* N1: missing item discovered around 18h05
* N2: staff badge required for corridor
* N3: badge log entry at 17h58
* N4: café receipt at 17h52
* N5: witness clothing description
* N6: torn note directional/time clue
* N7: latch/lock clue from vitrine
* N8: drop location clue

## Edge examples

* N3 contradicts claimed location
* N4 supports or refutes alibi
* N7 narrows method
* N6 narrows drop target
* combined N3 + N4 can expose false timeline

## v1.0 requirement

At least one valid resolution must require use of a contradiction, not only physical recovery.

---

# 13) Dialogue Model — v1.0 vs Later

## v1.0 dialogue model

The first implementation uses **structured deterministic dialogue scenes**.

Each scene defines:

* available intents
* required slots
* legal fact reveals
* trust/stress effects
* refusal states
* repair states
* French stems
* summary checks
* unlock outputs

This must be playable **without a live LLM dependency**.

## Later dialogue model

A future LLM may act only as a **surface adapter** for:

* interpreting player wording
* rephrasing legal responses
* generating natural style
* offering repair prompts

It may **never invent facts** outside allowed fact slices.

## Hard rule

No LLM integration before:

* allowed-fact slices exist
* scene states exist
* deterministic fallback exists
* transcript replay exists

---

# 14) Dialogue Scenes (Structured)

## S1 — Lobby Intro (Élodie)

### Goal

Establish incident and grant inspection permission.

### Player skills

* ask what happened
* ask when
* ask permission

### Key stems

* “Qu’est-ce qui s’est passé ?”
* “À quelle heure ?”
* “Est-ce que je peux regarder… ?”

### Unlocks

* vitrine inspection
* pointer to Marc

## S2 — Security Gate (Marc)

### Goal

Gain log access or procedure clue.

### Success paths

* polite request
* correct `vous` usage
* coherent summary of why access matters
* return with binder/procedure support

### Failure

* denied for now
* must use alternate route or recover trust

## S3 — Timeline Witnessing (Samira or equivalent)

### Goal

Build room/time sequence.

### Skills

* ask where
* ask when
* ask who
* ask what they saw

### Check

* short French summary

## S4 — Café Witness (Jo)

### Goal

Get clothing/timestamp clue.

### Mechanic

* witness dialogue + receipt reading

### Time sensitivity

* if late, memory quality drops

## S5 — Confrontation / Recovery

### Goal

Recover item or accuse correctly.

### Minimum proof requirement

Player must present at least two facts in French, including one contradiction or corroboration chain.

### Example forms

* “Vous étiez à ___ à ___.”
* “Le reçu montre ___.”
* “Le badge indique ___.”

---

# 15) French Learning Layer (Narrow v1.0 Scope)

This is a **scene-bound scaffolding policy**, not a generalized pedagogy engine.

## Target band

A1 → light A2

## Core language goals

* who / what / where / when / why
* time expressions
* polite requests
* simple passé composé
* clothing/basic descriptors
* short summaries

## Scaffolding ladder

1. soft hint on state card or inspect panel
2. sentence stem with one blank
3. multiple-choice rephrase
4. English meta-help allowed, but French action still required

## Difficulty profiles

### D0

* slower dialogue
* fewer idioms
* more confirmations
* stronger hints

### D1

* less prompting
* more natural phrasing
* slightly harder summaries

### D2+ (future extension)

Not required for initial ship.

---

# 16) Minigames (MBAM-Specific, Deterministic)

No generalized minigame framework is required beyond these four.

## MG1 — Wall Label Reading

Prompt:

* find title
* find date

Use:

* reading comprehension
* gallery clue anchor

## MG2 — Badge Log Read

Prompt:

* identify important entry
* state key time

Use:

* access/timeline contradiction

## MG3 — Receipt Reading

Prompt:

* identify time and item

Use:

* alibi validation

## MG4 — Torn Note Reconstruction

Prompt:

* fill three missing words from small set

Use:

* drop clue / meeting clue

---

# 17) Investigation UI Shell (v1.0)

The frontend must evolve from viewer into a minimal investigation shell.

## Required UI pieces

* inspect/action panel
* dialogue panel
* NPC state card area
* evidence tray / notebook
* contradiction/timeline view
* case resolution panel

## Not required yet

* large generalized quest log
* multi-case journal system
* broad inventory simulation

---

# 18) Success / Failure Conditions

## Win

* recover item
* or identify culprit with sufficient corroborated evidence

## Best outcome

* recovered quietly
* no public escalation
* good trust with Élodie and Marc
* at least two accurate French summaries
* correct polite usage on key gates

## Soft fail

* wrong accusation
* item leaves building
* relationship penalty for future continuity

## v1.0 requirement

Each shipped seed must support:

* one success path through evidence recovery
* one success path through accusation/reasoning
* one soft-fail branch

---

# 19) Canonical Data Model Contract

These model semantics are frozen enough to build against.

## WorldState

Physical truth only:

* rooms
* doors
* objects
* positions
* time
* physical flags

## CaseState

Canonical case truth:

* seed
* cast overlays
* roles
* alibi matrix
* timeline schedule
* truth graph
* evidence placement
* scene gates
* endings

## NPCState

Per-runtime actor state:

* current room
* availability
* trust
* stress
* stance
* visible behavior flags
* known_fact_flags
* current scene state

## CastRegistry

Persistent identity layer:

* npc_id
* name
* baseline traits
* baseline register
* tell profile
* portrait/state-card config

## DialogueSceneState

Deterministic conversation state:

* scene_id
* npc_id
* allowed_intents
* revealed_fact_ids
* required_slots
* trust/stress gates
* summary requirement
* completion state

## DialogueTurnContext

Future adapter input:

* npc_id
* scene_state
* allowed_facts
* player_utterance
* learning_targets
* hint_level
* player_profile

These structures do not need to be future-perfect, but Phase 1 work should not reopen their basic semantics.

---

# 20) Voice-Ready Boundary (But Not Voice-Required Yet)

The system should anticipate voice later.

## Player input abstraction should support

* text input
* parsed intent
* optional speech transcript
* optional pronunciation feedback slot

## But

Voice interaction is **not required** for MBAM v1.0.

---

# 21) Shipping Seeds

## Seed A

* Culprit = Outsider
* Method = delivery_cart_swap
* Ally = Guard

## Seed B

* Culprit = Intern
* Method = badge_borrow
* Ally = Barista

## Seed C

* Culprit = Donor
* Method = case_left_unlatched
* Ally = Curator

Same cast, same rooms, different truth structure, clue composition, and timing emphasis.

---

# 22) First Playable Acceptance Criteria

The first playable version of MBAM is achieved when all of the following are true:

* one seed can be loaded deterministically
* the MBAM location loads with the correct rooms and props
* the five fixed characters exist in the runtime
* key MBAM objects can be inspected/interacted with
* at least core evidence can be discovered
* at least one contradiction can be unlocked and used
* the player can complete structured dialogue scenes
* the player can reach at least one valid recovery or accusation ending
* replaying the same seed produces the same truth and same legal outcomes
* the case can be exported/replayed/debugged through the existing artifact pipeline

This is the target for the first true vertical-slice milestone.

---

# 23) Technical Non-Goals and Deferrals

These are explicitly deferred and must not block v1 implementation start:

* live websocket-first host runtime
* full voice interaction
* generalized content framework
* generalized social simulation
* generalized clue-board framework
* generalized minigame framework
* broad inventory simulation
* polished production asset pipeline
* full LLM dialogue adapter
* broad pathfinding/general nav expansion unless directly required by MBAM

---

# 24) Current Repo Constraints Triage

## Do not block Phase 1

These may remain imperfect while Phase 1 begins:

* missing full live websocket host path
* debug-heavy frontend
* lack of frontend test suite
* viewer-oriented UI shell
* leftover naming residue in some frontend/viewer paths
* weak live-mode schema guarantees

## Must be addressed during implementation

These are central missing layers:

* no canonical `CaseState`
* no `CastRegistry`
* no MBAM `NPCState` semantics
* no object affordance/state system
* no contradiction/evidence engine
* no structured deterministic dialogue scene layer
* no resolution logic
* no scaffolding/minigame implementation

## Can wait unless they interfere directly

* PHASE_E scheduler/runtime issue
* deeper ECS cleanup
* broad pathfinding improvements
* full LLM truth-guard runtime path
* generalized runtime/event cleanup outside MBAM needs

---

# 25) Implementation Order Lock

The execution order is locked as:

1. **Canonical MBAM Case Bundle**
2. **Cast Registry + seeded role overlays + NPCState**
3. **Object affordances + evidence/contradiction loop**
4. **Deterministic structured dialogue scenes**
5. **Frontend investigation shell**
6. **French scaffolding + MG1–MG4**
7. **Replay polish + endings / ship validation**
8. **Optional LLM dialogue adapter**

This order should not be inverted without a strong repo-grounded reason.

---

# 26) First Task Definition

The first implementation task is:

## Task 1

Implement the canonical **MBAM Case Bundle (`CaseState`)** with:

* deterministic seed fixtures for **A / B / C**
* role assignment
* cast overlays
* timeline schedule
* evidence placement
* alibi matrix
* truth graph
* scene gates
* resolution rules
* same-seed determinism tests
* cross-seed variation tests
* solvability-oriented fixtures for shipped seeds

This is the cleanest first move because it establishes the canonical non-physical truth layer before interaction and dialogue are built on top of it.

---

# 27) Non-Negotiable Rules

* **Case Truth is canonical.**
* **World Truth does not own mystery truth.**
* **Dialogue may adapt truth presentation, never truth content.**
* **The first playable version must work without a live LLM.**
* **MBAM v1.0 is a vertical slice, not a generalized platform.**
* **Every shipped seed must be deterministic and solvable.**
* **French scaffolding must support progress, not bypass it.**
* **State cards are gameplay hints, not decoration.**
* **Recurring cast identity is a core system, not flavor content.**
* **Offline replay/debug is a priority feature for development and validation.**

---

# 28) Phase 0 Completion Checklist

Phase 0 is complete when the following are all true:

* the v1 definition is locked
* truth-layer boundaries are locked
* canonical MBAM content scope is frozen
* data model semantics are frozen enough to build against
* first playable acceptance criteria are defined
* non-goals/deferrals are explicit
* current repo constraints are triaged
* implementation order is locked
* the first implementation task is defined

This spec is intended to satisfy that checklist.
