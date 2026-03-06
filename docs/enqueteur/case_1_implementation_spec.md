**Revised and tightened Case 1 implementation spec** for **MBAM**, updated to reflect the adjustments:

* **v1.0 is a vertical slice, not a full platform**
* **Case Truth is centralized and canonical**
* **structured deterministic dialogue comes before real LLM dialogue**
* **French scaffolding starts as a narrow scene policy**
* **recurring cast identity is a core system**
* **state-card portrait logic is explicitly modeled**
* **offline replay/debug is prioritized over live runtime polish**
* **voice is anticipated architecturally, but not required for initial implementation**

---

# Case 1 Spec — MBAM (Revised)

## Title

**Le Petit Vol du Musée**
Tagline: *“Un petit objet. Un grand embarras.”*

---

# 0) Scope Lock — What Enquêteur v1.0 Means

This spec defines **Enquêteur v1.0** as a **single fully playable deterministic case vertical slice**.

## Enquêteur v1.0 must include

* one case: **MBAM / Le Petit Vol du Musée**
* one fixed location set
* one fixed recurring cast of five characters
* **three deterministic seeds** (A/B/C)
* object-based investigation
* deterministic case truth + replayability
* structured French dialogue interactions
* narrow French scaffolding for A1–A2
* one accusation/recovery resolution loop
* offline replay/debug support

## Enquêteur v1.0 does **not** require

* a generalized multi-case framework
* generic content pipelines beyond what MBAM needs
* fully live websocket-first play
* production voice support
* fully autonomous LLM dialogue at first implementation
* generalized minigame framework beyond the four MBAM minigames

This is a **case-first implementation**, not a platform-first implementation.

---

# 1) Core Architecture Lock

Enquêteur uses three strictly separated truth layers.

## Layer A — World Truth

Owned by Sim4 runtime.

This includes:

* rooms
* doors
* objects
* agent positions
* item locations
* world clock
* movement
* world mutations
* availability and reachability

## Layer B — Case Truth

Owned by the deterministic case bundle.

This includes:

* culprit
* method
* motive
* drop location
* seeded role overlays
* clue graph
* evidence placement
* alibi matrix
* timeline beats
* win/fail rules
* scene/dialogue gates

## Layer C — Dialogue/Pedagogy Adapter

Owned by the dialogue/scaffolding layer.

This includes:

* interpreting player input
* selecting legal response options
* revealing only allowed facts
* hint tiers
* sentence stems
* comprehension checks
* French difficulty tuning
* state-card presentation

## Hard rule

**Case Truth is canonical for all non-physical gameplay logic.**
No core mystery truth may be invented or stored only in:

* frontend UI state
* ad hoc NPC runtime memory
* object-local behavior alone
* LLM output

---

# 2) Design Goals

* **A1–A2 playable** on first run.
* **Replayable** through deterministic seeded variation.
* **Living world feel** through visible movement, room presence, and timing pressure.
* **Recurring cast** with persistent identities but changing seeded roles.
* **Deterministic solvability** in every shipped seed.
* **LLM-safe architecture** where dialogue style can become dynamic later without owning truth.
* **Pixi-friendly scope** with clear readable spaces and prop-based clue interactions.

---

# 3) World Layout (Pixi-Friendly)

Represented as Sim4-style rooms with simple readable geometry.

## Rooms

1. **MBAM Lobby** (public)
2. **Gallery 1 — Salle des Affiches** (semi-public)
3. **Security Office** (restricted)
4. **Service Corridor** (restricted)
5. **Café de la Rue** (public)

## Connections / Gates

* Lobby ↔ Gallery 1: open
* Lobby ↔ Security Office: restricted; requires permission / escort / trust gate
* Gallery 1 ↔ Service Corridor: restricted; guard-controlled
* Lobby ↔ Café: open

## Visual Prop Goals

Minimal, readable, mostly static:

* **Lobby**: reception desk, coat rack, brochure stand, scanner
* **Gallery**: vitrine, wall label, bench, camera dome
* **Security Office**: terminal, binder, lanyards, radio dock
* **Corridor**: cart, bin, keypad door
* **Café**: counter, receipt printer, board, queue markers

---

# 4) MBAM Case Bundle (Canonical Case Truth)

This is the most important gameplay object in the case.

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

# 5) Cast Registry (Persistent Recurring Characters)

The five MBAM characters are not disposable NPCs.
They are a **persistent cast layer** with stable identity plus seeded case overlays.

## NPC1 — Curator: **Élodie Marchand**

* identity: curator
* baseline traits: proud, precise, impatient with vagueness
* baseline speech: formal French
* tell pattern: insists on exact wording and exact time
* trust trigger: polite register, accurate summaries
* anti-trigger: sloppy accusations

## NPC2 — Guard: **Marc Dutil**

* identity: security guard
* baseline traits: procedural, tired, rule-bound
* baseline speech: short, direct, protocol-focused
* tell pattern: hides behind process
* trust trigger: competence + respectful tone
* anti-trigger: trying to skip procedure

## NPC3 — Intern: **Samira B.**

* identity: intern
* baseline traits: anxious, eager, oversharing
* baseline speech: simpler French, some anglicisms
* tell pattern: too many details when nervous
* trust trigger: reassurance, calm pacing
* anti-trigger: direct pressure too early

## NPC4 — Donor: **Laurent Vachon**

* identity: donor/VIP
* baseline traits: polished, status-aware, defensive
* baseline speech: polished French, may code-switch to English if irritated
* tell pattern: avoids exact times
* trust trigger: formal address, tact
* anti-trigger: perceived disrespect

## NPC5 — Barista: **Jo Leclerc**

* identity: barista/witness
* baseline traits: observant, casual, social
* baseline speech: Montreal casual French, idioms scaled by difficulty
* tell pattern: remembers vibe/clothes before names
* trust trigger: friendliness, specificity
* anti-trigger: stiff interrogation tone

## Cast overlay model

Each run applies a seeded overlay:

* role in this case
* degree of helpfulness
* what they know
* what they believe
* what they hide
* what they misremember
* state-card display profile

---

# 6) State Cards / Portrait Hint System

This is a core gameplay layer, not just flavor UI.

Each major dialogue turn can display a **state card** showing:

* portrait/state art variant
* emotional state
* stance
* soft alignment hint
* trust trend
* tell cue
* suggested interaction mode

## State dimensions

### Emotion

* calm
* stressed
* amused
* annoyed
* nervous
* guarded

### Stance

* helpful
* procedural
* evasive
* defensive
* manipulative
* flustered

### Alignment hint

Not explicit truth labels, but soft tendencies such as:

* protecting institution
* protecting self
* protecting someone else
* trying to save face
* trying to help quietly

## Use in gameplay

State cards provide clues about:

* tone to use
* whether to ask direct or indirect questions
* whether to use `vous`
* whether contradiction pressure is safe
* whether the NPC is hiding guilt or simply discomfort

---

# 7) World Objects + MBAM-Specific Affordances

Objects must support case-specific interactions first.
Generalization can happen later.

## O1 — Display Case (vitrine)

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
* can support early suspicion

---

## O2 — Missing Item: **Le Médaillon**

### State

* `present|missing|recovered`
* `location`
* `examined:boolean`

### Affordances

* `examine()`

### Case use

* recovered item provides inscription clue or confirmation detail

---

## O3 — Wall Label (cartel)

### State

* `text_variant_id`

### Affordances

* `read()`

### Case use

* **MG1**
* extracts title/date
* doubles as French reading task

---

## O4 — Bench

### State

* `under_bench_item:boolean`

### Affordances

* `inspect()`

### Case use

* may reveal torn note fragment or dropped paper

---

## O5 — Visitor Logbook

### State

* entries list
* scribble pattern

### Affordances

* `read()`

### Case use

* supports who-was-present reasoning
* mild role/context clue

---

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

---

## O7 — Security Binder

### State

* `page_state`

### Affordances

* `read()`

### Case use

* reveals procedure rule
* helps regain access path if terminal gate is missed

---

## O8 — Keypad Door

### State

* `locked`
* `code_hint`

### Affordances

* `inspect()`
* `attempt_code()` (optional branch)

### Case use

* reinforces access restrictions

---

## O9 — Receipt Printer / Café Receipts

### State

* `recent_receipts:[{time, item}]`

### Affordances

* `ask_for_receipt()`
* `read_receipt()`

### Case use

* **MG3**
* supports/refutes alibi timing

---

## O10 — Bulletin Board

### State

* flyer text

### Affordances

* `read()`

### Case use

* optional vocab / world texture reward

---

## Evidence Items

### E1 — Torn Note

* `reconstruct()`
* **MG4**
* yields meeting/drop clue

### E2 — Café Receipt

* inventory evidence item
* used in contradiction or alibi challenge

### E3 — Lanyard Fiber / Sticker

* environmental evidence
* links to cart/badge-related method

---

# 8) Timeline Structure (Real-Time, Deterministic, Branchy)

The world clock runs continuously, but case beats are deterministically scheduled.

## Baseline beats

* **T+00** player arrives; medallion already missing
* **T+02** curator begins containment mode
* **T+05** guard patrol shift / movement change
* **T+08** intern transitions rooms
* **T+10** donor appears or calls
* **T+12** barista witness window is strongest
* **T+15** terminal log archival / increased access friction

## Time-pressure rules

* waiting changes witness quality
* waiting can reduce evidence visibility
* waiting can move NPCs
* early confrontation with weak evidence reduces trust
* missed clue windows must remain recoverable by alternate path, but harder

## v1.0 rule

Every shipped seed must remain solvable even if the player misses the optimal path.

---

# 9) Evidence + Contradiction Graph

This is part of **Case Truth**, not a UI convenience.

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

At least one valid resolution must require the player to use a contradiction, not just find a dropped item.

---

# 10) Dialogue Model — v1.0 vs Later

## v1.0 dialogue model

The first implementation must use **structured deterministic dialogue scenes**.

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

This should be playable **without any live LLM dependency**.

## Later dialogue model

An LLM may later act as a **surface adapter only**:

* interpreting player wording
* rephrasing legal NPC responses
* generating natural style
* offering repair prompts
* never inventing facts outside allowed slices

## Hard rule

No LLM integration before:

* allowed-facts slices exist
* scene states exist
* deterministic fallback exists
* transcript replay exists

---

# 11) Dialogue Scenes (Structured)

## Scene S1 — Lobby Intro (Élodie)

### Goal

Establish the incident and grant inspection permission.

### Player skills

* ask what happened
* ask when
* ask permission

### Key stems

* “Qu’est-ce qui s’est passé ?”
* “À quelle heure ?”
* “Est-ce que je peux regarder… ?”

### Unlock

* vitrine inspection
* pointer to Marc

---

## Scene S2 — Security Gate (Marc)

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

---

## Scene S3 — Timeline Witnessing (Samira or equivalent)

### Goal

Build room/time sequence.

### Skills

* ask where
* ask when
* ask who
* ask what they saw

### Check

* short French summary

---

## Scene S4 — Café Witness (Jo)

### Goal

Get clothing/timestamp clue.

### Mechanic

* witness dialogue + receipt reading

### Time sensitivity

If late, memory quality drops.

---

## Scene S5 — Confrontation / Recovery

### Goal

Recover item or accuse correctly.

### Minimum proof requirement

Player must present at least two facts in French, including one contradiction or corroboration chain.

### Example forms

* “Vous étiez à ___ à ___.”
* “Le reçu montre ___.”
* “Le badge indique ___.”

---

# 12) French Learning Layer (Narrow v1.0 Scope)

This is a **scene-bound scaffolding policy**, not a giant generalized pedagogy engine.

## Target band

A1 → light A2

## Core language goals

* who / what / where / when / why
* time expressions
* polite requests
* simple passé composé
* clothing and basic descriptors
* short summaries

## Scaffolding ladder

1. soft hint on state card or inspect panel
2. sentence stem with one blank
3. multiple-choice rephrase
4. English meta-help allowed, but French action still required

## Difficulty profiles for v1.0

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

# 13) Minigames (MBAM-Specific, Deterministic)

No generic minigame framework required in v1.0 beyond these four.

## MG1 — Wall Label Reading

Prompt:

* find title
* find date

Use:

* reading comprehension
* gallery clue anchor

---

## MG2 — Badge Log Read

Prompt:

* identify important entry
* state key time

Use:

* access/timeline contradiction

---

## MG3 — Receipt Reading

Prompt:

* identify time and item

Use:

* alibi validation

---

## MG4 — Torn Note Reconstruction

Prompt:

* fill three missing words from small set

Use:

* drop clue / meeting clue

---

# 14) Investigation UI Shell (v1.0)

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

# 15) Success / Failure Conditions

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
* relationship penalty for future case continuity

## v1.0 requirement

Each shipped seed must support:

* one success path through evidence recovery
* one success path through accusation/reasoning
* one soft-fail branch

---

# 16) Data Structures (Revised)

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

---

# 17) Voice-Ready Boundary (But Not Voice-Required Yet)

The system should anticipate voice later.

## Therefore

Player input should already be abstracted as:

* text input
* parsed intent
* optional speech transcript
* optional pronunciation feedback slot

## But

Voice interaction is **not required** for MBAM v1.0 implementation.

---

# 18) Seeds (Shipping Set)

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

Same cast, same rooms, different truth structure, timing emphasis, and clue composition.

---

# 19) Implementation Priorities (Execution Order)

## Priority 1

Canonical MBAM Case Bundle

## Priority 2

Cast Registry + seeded role overlays

## Priority 3

Object affordances + evidence/contradiction loop

## Priority 4

Deterministic structured dialogue scenes

## Priority 5

Frontend investigation shell

## Priority 6

French scaffolding + MG1–MG4

## Priority 7

Optional LLM dialogue adapter

## Priority 8

Replay polish and ship validation

---

# 20) Non-Negotiable Rules

* **Case Truth is canonical.**
* **World Truth does not own mystery truth.**
* **Dialogue may adapt truth presentation, never truth content.**
* **The first playable version must work without a live LLM.**
* **MBAM v1.0 is a vertical slice, not a generalized platform.**
* **Every shipped seed must be deterministic and solvable.**
* **French scaffolding must support progress, not bypass it.**
* **State cards are gameplay hints, not decoration.**

---

If you want, next I can turn this revised spec into either:

1. a **Codex execution brief for Phase 1–3**, or
2. a **formal JSON/data-model spec** for `CaseState`, `CastRegistry`, `NPCState`, and `DialogueSceneState`.
