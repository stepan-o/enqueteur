Here is the **most up-to-date phased plan** with the numbering cleaned up so it matches the **current locked execution order** and the work Codex has already been doing.

The main correction is:

* the old standalone **“Evidence / Contradiction Loop”** phase is now **absorbed into Phase 3**
* **Phase 4** is now correctly **Deterministic Structured Dialogue Scenes**

---

# Enquêteur v1.0 — Updated Implementation Phases

From the current repo state, the implementation phases to reach a **fully working Enquêteur v1.0** are:

# Phase 0 — Lock the playable target

Before writing more systems, lock what “done” means.

For v1, that means:

* one playable MBAM case
* three deterministic seeds A/B/C
* five fixed recurring characters
* one complete investigation loop
* structured deterministic dialogue without requiring a live LLM
* four MBAM minigames
* one accusation/recovery ending flow
* offline replay/debug support

This phase exists to stop the project from drifting into generic engine/platform work.

---

# Phase 1 — Canonical MBAM Case Bundle

Build the **Case Truth layer** first.

The repo already had:

* world runtime
* MBAM layout
* deterministic tick/replay spine

What it did **not** have was the actual deterministic mystery brain.

This phase adds:

* `CaseState`
* deterministic seed fixtures/generation for A/B/C
* role assignment
* cast overlays
* timeline beats
* evidence placement
* alibi matrix
* truth graph
* contradiction graph structure
* scene gates
* resolution rules
* visible vs hidden fact slices
* minimal runtime/export integration for case state

This is the canonical source of truth for all non-physical gameplay logic.

---

# Phase 2 — Cast Registry + Runtime NPC Layer

Add the fixed recurring cast as a real system.

This phase defines:

* `CastRegistry` for Élodie, Marc, Samira, Laurent, Jo
* baseline traits and registers
* tell profiles
* portrait/state-card config
* seeded per-run overlays
* `NPCState` runtime layer for:

    * trust
    * stress
    * stance
    * emotion
    * availability
    * room presence
    * known/believed/hidden/misremembered fact flags
    * schedule state
    * card-state metadata
* minimal runtime schedule/availability substrate
* NPC semantic projection for replay/debug/export

This phase turns “agents in rooms” into actual case actors.

---

# Phase 3 — MBAM Object Affordances + Investigation Substrate

The repo had rooms and props, but not case-ready investigation behavior.

This phase adds:

* MBAM-specific object state for O1–O10
* canonical affordance definitions like:

    * `inspect`
    * `read`
    * `check_lock`
    * `examine_surface`
    * `request_access`
    * `view_logs`
    * `ask_for_receipt`
    * `read_receipt`
    * `attempt_code`
    * `reconstruct`
    * `examine`
* deterministic prerequisite checks
* minimal player investigation command contract
* deterministic affordance execution
* evidence reveal / discovery / collection state
* fact unlock linkage
* contradiction linkage
* accusation prerequisite groundwork
* investigation-state projection for replay/debug/export

This phase is where the viewer becomes an actual investigation game substrate.

## Important note

What used to be described as a separate **“Evidence / Contradiction Loop”** phase is now included here.

That means Phase 3 already covers:

* clue discovery state
* contradiction detection/linkage
* fact unlock conditions
* evidence linking
* accusation prerequisites groundwork
* progress derived from discovered facts rather than loose scripting

This matters because Enquêteur is not just “find objects.” At least one valid path must require actual contradiction use.

---

# Phase 4 — Deterministic Structured Dialogue Scenes

Before any real LLM dialogue, build the deterministic scene system.

This phase implements:

* `DialogueSceneState`
* structured dialogue domain models
* canonical intent catalog
* S1–S5 scene definitions
* scene gating
* deterministic scene execution
* allowed intents
* required slots
* legal fact reveals
* trust/stress gates
* refusal/repair states
* French stems
* summary-check substrate
* scene unlock outputs
* dialogue transcript/state projection for replay/debug/export

At the end of this phase, the case should already be playable in a structured way **without a live model**.

---

# Phase 5 — Frontend Investigation Shell

The frontend is currently a strong Pixi viewer/dev shell. Now it has to become a game shell.

This phase adds:

* interaction/action panel from the existing inspect panel
* dialogue panel
* NPC state-card display area
* notebook/evidence tray
* contradiction/timeline view
* case resolution panel

The current rendering, focus, selection, replay, and overlay systems are already a strong base. This phase turns them into actual investigation UX.

---

# Phase 6 — French Scaffolding + MBAM Minigames

Only after the investigation loop works should the explicit language-learning layer be added.

This phase adds:

* scene-bound scaffolding policy
* hint ladder
* D0/D1 difficulty behavior
* MG1 label reading
* MG2 badge log
* MG3 receipt reading
* MG4 torn note reconstruction
* short French summary checks
* deterministic grading/gating

This should stay narrow and case-specific for v1.

---

# Phase 7 — Resolution, Replay, and Ship Validation

Then finish the vertical slice as a product-quality deterministic case.

This phase adds:

* win/fail/best-ending evaluator
* recovery path and accusation path validation
* soft-fail branch logic
* run summary / recap
* seed selector and replay polish
* full deterministic end-to-end tests for A/B/C
* artifact verification for complete runs

This phase makes MBAM shippable and debuggable.

---

# Phase 8 — Optional LLM Dialogue Adapter

Only after all of the above is working should the live LLM layer be introduced.

This phase adds:

* adapter-only dialogue layer
* allowed-facts enforcement
* natural-language phrasing on top of deterministic scene truth
* repair/rephrase behavior
* transcript logging and replay compatibility

The LLM should never own truth, only presentation.

---

## In one line, the path is:

**Case Bundle → Cast/NPC layer → Object interactions + evidence/contradiction substrate → Deterministic dialogue scenes → Frontend investigation shell → French scaffolding/minigames → Endings/replay polish → optional LLM adapter**

---

## Most practical foundation chunks

The cleanest foundational implementation order is:

1. `CaseState` + seed fixtures A/B/C
2. `CastRegistry` + `NPCState`
3. MBAM object affordance/state model + investigation command contract
4. evidence / fact unlock / contradiction linkage
5. deterministic dialogue scenes S1–S5

That remains the cleanest path from the current repo to a real v1 foundation.

---

## Current completion status

Based on the implementation flow so far:

* **Phase 0** — complete
* **Phase 1** — complete
* **Phase 2** — complete
* **Phase 3** — complete
* **Phase 4** — next

---

## Short version of the numbering fix

Old version:

* Phase 4 = Evidence / Contradiction Loop
* Phase 5 = Deterministic Dialogue Scenes

Updated version:

* Phase 3 = Object affordances **plus** evidence / contradiction substrate
* Phase 4 = Deterministic Dialogue Scenes

That is the version you should save going forward.

If you want, I can also rewrite this into a **very short project tracker version** with one paragraph per phase for easier reference.
