From the **current repo state** Codex described, the implementation phases to reach a **fully working Enquêteur v1.0** should be these:

# Phase 0 — Lock the playable target

Before writing more systems, lock what “done” means.

For v1, that means:

* one playable MBAM case
* three deterministic seeds A/B/C
* five fixed recurring characters
* one complete investigation loop
* structured dialogue without requiring a live LLM
* four MBAM minigames
* one accusation/recovery ending flow
* offline replay/debug support

This phase exists to stop the project from drifting into “generic engine work.”

# Phase 1 — Canonical MBAM Case Bundle

Build the **Case Truth layer** first.

This is the biggest missing piece in the current repo. The repo already has:

* world runtime
* MBAM layout
* deterministic tick/replay spine

What it does **not** have is the actual mystery brain.

This phase adds:

* `CaseState`
* seed generator for A/B/C
* role assignment
* cast overlays
* timeline beats
* evidence placement
* alibi matrix
* contradiction/truth graph
* resolution rules
* visible vs hidden fact slices

This is the core source of truth for all non-physical gameplay logic.

# Phase 2 — Cast Registry + Runtime NPC Layer

Next, add the fixed recurring cast as a real system.

The repo does not yet have a proper persistent cast identity layer, so this phase defines:

* `CastRegistry` for Élodie, Marc, Samira, Laurent, Jo
* baseline traits and registers
* tell profiles
* portrait/state-card config
* seeded per-run overlays
* `NPCState` runtime layer for trust, stress, stance, availability, room presence, and known fact flags

This phase turns “agents in a room” into actual case actors.

# Phase 3 — MBAM Object Affordances + Investigation Substrate

The repo has rooms and props, but not case-ready interactions.

This phase adds:

* MBAM-specific object state for O1–O10
* affordances like `inspect`, `read`, `check_lock`, `view_logs`, `ask_for_receipt`
* evidence spawning/revealing
* deterministic prerequisite checks
* minimal evidence inventory model
* player action command contract for investigation actions

This is where the viewer starts becoming an investigation game.

# Phase 4 — Evidence / Contradiction Loop

Now connect interactions to reasoning.

This phase adds:

* clue discovery state
* contradiction detection logic
* fact unlock conditions
* evidence linking
* accusation prerequisites
* case progress derived from discovered facts, not loose scripting

This matters because Enquêteur is not just “find objects.” At least one valid path must require actual contradiction use.

# Phase 5 — Deterministic Structured Dialogue Scenes

Before any real LLM dialogue, build the deterministic scene system.

This phase implements:

* `DialogueSceneState`
* S1–S5 scene flow
* allowed intents
* required slots
* legal fact reveals
* trust/stress gates
* refusal/repair states
* French stems
* summary checks
* scene unlock outputs

At the end of this phase, the case should already be playable in a structured way without a live model.

# Phase 6 — Frontend Investigation Shell

The frontend is currently a strong Pixi viewer/dev shell. Now it has to become a game shell.

This phase adds:

* interaction/action panel from the existing inspect panel
* dialogue panel
* NPC state-card display area
* notebook/evidence tray
* contradiction/timeline view
* case resolution panel

The current rendering, focus, selection, replay, and overlay systems are already a strong base. This phase turns them into actual investigation UX.

# Phase 7 — French Scaffolding + MBAM Minigames

Only after the investigation loop works should the full language-learning layer be added.

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

# Phase 8 — Resolution, Replay, and Ship Validation

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

# Phase 9 — Optional LLM Dialogue Adapter

Only after all of the above is working should the live LLM layer be introduced.

This phase adds:

* adapter-only dialogue layer
* allowed-facts enforcement
* natural language phrasing on top of deterministic scene truth
* repair/rephrase behavior
* transcript logging and replay compatibility

The LLM should never own truth, only presentation.

---

## In one line, the path is:

**Case Bundle → Cast/NPC layer → Object interactions → Evidence/contradiction logic → Deterministic dialogue scenes → Frontend investigation shell → French scaffolding/minigames → Endings/replay polish → optional LLM adapter**

---

## If you want the most practical “first 5 implementation chunks” from the current repo, they should be:

1. `CaseState` + seed fixtures A/B/C
2. `CastRegistry` + `NPCState`
3. MBAM object affordance/state model
4. contradiction/evidence graph integration
5. deterministic dialogue scenes S1–S5

That is the cleanest path from the current repo to a real v1 foundation.
