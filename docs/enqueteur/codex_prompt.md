You are joining the Enquêteur project as the implementation agent.

You should assume the following is already locked and must be treated as the source of truth unless explicitly revised:
- Enquêteur v1.0 is a **single deterministic vertical slice**, not a generalized platform build
- Case 1 is **MBAM — Le Petit Vol du Musée**
- Sim4 runtime provides **World Truth**
- a deterministic case bundle provides **Case Truth**
- dialogue/pedagogy layer provides **presentation/scaffolding**, not truth ownership
- the first playable implementation must work **without requiring a live LLM**
- any later LLM integration is **adapter-only**
- recurring cast identity is a **core system**
- state cards are **gameplay hints**, not decorative flavor
- offline replay/debug is more important than live-runtime polish for the first slice

Your job is to implement Enquêteur in a disciplined, case-first way.

You are not here to generalize prematurely.
You are not here to redesign the project from scratch.
You are here to build the MBAM case vertical slice cleanly and deterministically on top of the current repo.

-----------------------------------
PROJECT LOCK: ENQUÊTEUR v1.0
-----------------------------------

Enquêteur v1.0 means:
- one case: MBAM / “Le Petit Vol du Musée”
- one recurring cast of five fixed characters
- three deterministic seeds A/B/C
- object-based investigation
- deterministic evidence/contradiction logic
- structured French dialogue scenes
- narrow A1–A2 scaffolding
- accusation/recovery resolution loop
- offline replay/debug support

It does NOT require:
- a generalized multi-case content pipeline
- production voice stack
- production live LLM play
- generic minigame framework beyond MBAM needs
- generalized quest/inventory framework beyond this case

-----------------------------------
ARCHITECTURE LOCK
-----------------------------------

There are three truth layers and they must remain separate.

1) WORLD TRUTH
   Owned by Sim4 runtime.
   Includes:
- rooms
- doors
- objects
- item locations
- positions
- world clock
- movement
- physical state mutations
- reachability / access

2) CASE TRUTH
   Owned by the deterministic MBAM case bundle.
   Includes:
- culprit
- ally
- misdirector
- method
- drop location
- evidence placement
- alibi matrix
- timeline beats
- contradiction graph
- scene gates
- resolution rules
- visible/hidden fact slices

3) DIALOGUE / PEDAGOGY ADAPTER
   Owned by dialogue and scaffolding layer.
   Includes:
- input interpretation
- allowed fact presentation
- repair/refusal prompts
- sentence stems
- hint levels
- summary checks
- state-card rendering metadata
- difficulty tuning

Hard rules:
- Case Truth is canonical for all non-physical gameplay logic.
- World Truth must not secretly own mystery truth.
- Dialogue layer may adapt wording and pacing, but may never invent or alter core truth.
- The first playable version must work without a live LLM.

-----------------------------------
CASE 1 LOCK: MBAM
-----------------------------------

Title:
Le Petit Vol du Musée

Tagline:
“Un petit objet. Un grand embarras.”

-----------------------------------
WORLD LAYOUT
-----------------------------------

Rooms:
1. MBAM Lobby
2. Gallery 1 — Salle des Affiches
3. Security Office
4. Service Corridor
5. Café de la Rue

Connections / gates:
- Lobby <-> Gallery 1: open
- Lobby <-> Security Office: restricted
- Gallery 1 <-> Service Corridor: restricted
- Lobby <-> Café: open

Key props by room:
- Lobby: reception desk, coat rack, brochure stand, scanner
- Gallery: vitrine, wall label, bench, camera dome
- Security Office: terminal, binder, lanyards, radio dock
- Corridor: cart, bin, keypad door
- Café: counter, receipt printer, board, queue markers

-----------------------------------
FIXED CAST
-----------------------------------

NPC1 — Élodie Marchand (Curator)
- baseline traits: proud, precise, impatient with vagueness
- register: formal French
- tell profile: exact wording, exact times
- trust triggers: polite register, accurate summaries
- anti-triggers: sloppy accusations

NPC2 — Marc Dutil (Guard)
- baseline traits: procedural, tired, rule-bound
- register: short, direct, protocol-focused French
- tell profile: hides behind procedure
- trust triggers: competence + respectful tone
- anti-triggers: trying to bypass process

NPC3 — Samira B. (Intern)
- baseline traits: anxious, eager, oversharing
- register: simpler French, occasional anglicisms
- tell profile: too many details when nervous
- trust triggers: calm reassurance
- anti-triggers: direct pressure too early

NPC4 — Laurent Vachon (Donor/VIP)
- baseline traits: polished, status-aware, defensive
- register: polished French, may code-switch if irritated
- tell profile: avoids exact times
- trust triggers: tact and formality
- anti-triggers: disrespect

NPC5 — Jo Leclerc (Barista/Witness)
- baseline traits: observant, casual, social
- register: Montreal casual French, idioms scaled by difficulty
- tell profile: remembers clothes/vibes before names
- trust triggers: friendly specificity
- anti-triggers: stiff interrogation tone

-----------------------------------
SEEDED ROLE OVERLAYS
-----------------------------------

Role slots:
- CULPRIT ∈ {Intern, Donor, Outsider}
- ALLY ∈ {Guard, Barista, Curator}
- MISDIRECTOR ∈ {Curator, Intern, Donor}
- METHOD ∈ {badge_borrow, case_left_unlatched, delivery_cart_swap}
- DROP ∈ {café bathroom stash, corridor bin, coat rack pocket}

Shipping seeds:
- Seed A: Culprit=Outsider, Method=delivery_cart_swap, Ally=Guard
- Seed B: Culprit=Intern, Method=badge_borrow, Ally=Barista
- Seed C: Culprit=Donor, Method=case_left_unlatched, Ally=Curator

Every shipped seed must be deterministic and solvable.

-----------------------------------
TIMELINE LOCK
-----------------------------------

Baseline beats:
- T+00 player arrives; medallion already missing
- T+02 curator enters containment mode
- T+05 guard patrol/position change
- T+08 intern movement beat
- T+10 donor arrives or calls
- T+12 barista witness window strongest
- T+15 terminal log archival / access friction increases

Rules:
- waiting changes NPC availability and clue quality
- waiting may reduce evidence visibility
- early confrontation with weak evidence reduces trust
- every seed must remain solvable even after missed optimal windows, but through harder alternate paths

-----------------------------------
OBJECTS + MBAM AFFORDANCES
-----------------------------------

O1 Display Case (vitrine)
State:
- locked|unlocked
- contains_item:boolean
- tampered:boolean
- latch_condition
  Affordances:
- inspect()
- check_lock()
- examine_surface()

O2 Missing Item — Le Médaillon
State:
- present|missing|recovered
- location
- examined:boolean
  Affordance:
- examine()

O3 Wall Label (cartel)
State:
- text_variant_id
  Affordance:
- read()
  Use:
- MG1 label reading

O4 Bench
State:
- under_bench_item:boolean
  Affordance:
- inspect()

O5 Visitor Logbook
State:
- entries list
- scribble pattern
  Affordance:
- read()

O6 Badge Access Terminal
State:
- online:boolean
- log_entries:[{badge_id, time, door}]
- archived:boolean
  Affordances:
- request_access()
- view_logs()
  Use:
- MG2 badge log

O7 Security Binder
State:
- page_state
  Affordance:
- read()

O8 Keypad Door
State:
- locked
- code_hint
  Affordances:
- inspect()
- attempt_code() [optional branch]

O9 Receipt Printer / Café Receipts
State:
- recent_receipts:[{time, item}]
  Affordances:
- ask_for_receipt()
- read_receipt()
  Use:
- MG3 receipt reading

O10 Bulletin Board
State:
- flyer text
  Affordance:
- read()

Evidence items:
E1 Torn Note
- reconstruct()
- MG4 torn-note reconstruction

E2 Café Receipt
- evidence item for alibi contradiction

E3 Lanyard Fiber / Sticker
- environmental clue tied to method/cart access

-----------------------------------
EVIDENCE / CONTRADICTION LOCK
-----------------------------------

Primary clue types:
- access clue
- time clue
- text clue
- contradiction clue
- location clue

Minimum viable clue nodes:
- N1 missing item discovered around 18h05
- N2 staff badge required for corridor
- N3 badge log entry at 17h58
- N4 café receipt at 17h52
- N5 witness clothing description
- N6 torn note directional/time clue
- N7 latch/lock clue from vitrine
- N8 drop location clue

At least one valid resolution path must require the player to use a contradiction, not only physical recovery.

-----------------------------------
DIALOGUE LOCK
-----------------------------------

v1.0 dialogue is structured and deterministic.

Each scene must define:
- allowed intents
- required slots
- legal fact reveals
- trust/stress effects
- refusal states
- repair states
- French stems
- summary checks
- unlock outputs

Core scenes:
S1 Lobby Intro (Élodie)
S2 Security Gate (Marc)
S3 Timeline Witnessing (Samira or equivalent)
S4 Café Witness (Jo)
S5 Confrontation / Recovery

No live LLM dependency is required for first playable implementation.

Later LLM integration is allowed only after:
- allowed-facts slices exist
- deterministic scene states exist
- fallback dialogue exists
- transcript replay exists

-----------------------------------
FRENCH LEARNING LOCK
-----------------------------------

Target:
A1 -> light A2

Core goals:
- who / what / where / when / why
- time expressions
- polite requests
- simple passé composé
- clothing/basic descriptors
- short summaries

Scaffolding ladder:
1. soft hint on state card or inspect panel
2. sentence stem with one blank
3. multiple-choice rephrase
4. English meta-help allowed, but French action still required

v1.0 difficulty profiles:
- D0
- D1

D2+ is not required for initial ship.

-----------------------------------
MINIGAME LOCK
-----------------------------------

MG1 Label Reading
- find title
- find date

MG2 Badge Log Read
- identify important entry
- state key time

MG3 Receipt Reading
- identify time and item

MG4 Torn Note Reconstruction
- choose missing words from small option set

No generalized minigame framework is required beyond these four for v1.0.

-----------------------------------
STATE CARDS LOCK
-----------------------------------

State cards are core gameplay hints.

Each relevant dialogue turn may surface:
- portrait/state variant
- emotion
- stance
- soft alignment hint
- trust trend
- tell cue
- suggested interaction mode

State dimensions:
Emotion:
- calm
- stressed
- amused
- annoyed
- nervous
- guarded

Stance:
- helpful
- procedural
- evasive
- defensive
- manipulative
- flustered

Soft alignment hints:
- protecting institution
- protecting self
- protecting someone else
- trying to save face
- trying to help quietly

-----------------------------------
SUCCESS / FAILURE LOCK
-----------------------------------

Win:
- recover item
- or identify culprit with sufficient corroborated evidence

Best outcome:
- recovered quietly
- no public escalation
- good trust with Élodie and Marc
- at least two accurate French summaries
- correct polite usage on key gates

Soft fail:
- wrong accusation
- item leaves building
- relationship penalty for future continuity

Each shipped seed must support:
- one recovery success path
- one accusation/reasoning success path
- one soft-fail branch

-----------------------------------
FORMAL DATA-MODEL SPEC
-----------------------------------

Below are the canonical v1.0 data models. Keep them deterministic and implementation-oriented. You may adapt field placement to actual repo conventions, but semantics must remain consistent.

1) CaseState

```json
{
  "case_id": "MBAM_01",
  "seed": "string",
  "difficulty_profile": "D0|D1",
  "runtime_clock_start": "string",
  "cast_overlay": {
    "elodie": {
      "role_slot": "CURATOR|MISDIRECTOR|ALLY",
      "helpfulness": "low|medium|high",
      "knowledge_flags": ["string"],
      "belief_flags": ["string"],
      "hidden_flags": ["string"],
      "misremember_flags": ["string"],
      "state_card_profile_id": "string"
    },
    "marc": {
      "role_slot": "GUARD|ALLY",
      "helpfulness": "low|medium|high",
      "knowledge_flags": ["string"],
      "belief_flags": ["string"],
      "hidden_flags": ["string"],
      "misremember_flags": ["string"],
      "state_card_profile_id": "string"
    },
    "samira": {
      "role_slot": "INTERN|CULPRIT|MISDIRECTOR",
      "helpfulness": "low|medium|high",
      "knowledge_flags": ["string"],
      "belief_flags": ["string"],
      "hidden_flags": ["string"],
      "misremember_flags": ["string"],
      "state_card_profile_id": "string"
    },
    "laurent": {
      "role_slot": "DONOR|CULPRIT|MISDIRECTOR",
      "helpfulness": "low|medium|high",
      "knowledge_flags": ["string"],
      "belief_flags": ["string"],
      "hidden_flags": ["string"],
      "misremember_flags": ["string"],
      "state_card_profile_id": "string"
    },
    "jo": {
      "role_slot": "BARISTA|ALLY",
      "helpfulness": "low|medium|high",
      "knowledge_flags": ["string"],
      "belief_flags": ["string"],
      "hidden_flags": ["string"],
      "misremember_flags": ["string"],
      "state_card_profile_id": "string"
    },
    "outsider": {
      "role_slot": "OUTSIDER|CULPRIT",
      "helpfulness": "none",
      "knowledge_flags": ["string"],
      "belief_flags": ["string"],
      "hidden_flags": ["string"],
      "misremember_flags": ["string"],
      "state_card_profile_id": "string|null"
    }
  },
  "roles_assignment": {
    "culprit": "samira|laurent|outsider",
    "ally": "marc|jo|elodie",
    "misdirector": "elodie|samira|laurent",
    "method": "badge_borrow|case_left_unlatched|delivery_cart_swap",
    "drop": "cafe_bathroom_stash|corridor_bin|coat_rack_pocket"
  },
  "timeline_schedule": [
    {
      "beat_id": "string",
      "time_offset_sec": 0,
      "type": "npc_move|availability_change|evidence_shift|access_change|witness_window|archive_event",
      "actor_id": "string|null",
      "location_id": "string|null",
      "preconditions": ["string"],
      "effects": ["string"]
    }
  ],
  "evidence_placement": {
    "display_case": {
      "tampered": true,
      "latch_condition": "intact|scratched|loose"
    },
    "bench": {
      "contains": "none|torn_note_fragment|receipt_fragment"
    },
    "corridor": {
      "contains": ["none|lanyard_fiber|sticker|cart_trace"]
    },
    "cafe": {
      "receipt_id": "string|null"
    },
    "drop_location": {
      "location_id": "cafe_bathroom_stash|corridor_bin|coat_rack_pocket",
      "contains_medallion": true
    }
  },
  "alibi_matrix": {
    "elodie": [
      {
        "time_window": "string",
        "location_claim": "string",
        "truth_value": "true|false|partial",
        "evidence_support": ["string"]
      }
    ],
    "marc": [],
    "samira": [],
    "laurent": [],
    "jo": []
  },
  "truth_graph": {
    "nodes": [
      {
        "fact_id": "N1",
        "type": "access|time|text|contradiction|location|method",
        "text": "string",
        "visibility": "hidden|discoverable|public",
        "source_ids": ["string"],
        "unlock_conditions": ["string"]
      }
    ],
    "edges": [
      {
        "edge_id": "string",
        "from_fact_id": "string",
        "to_fact_id": "string",
        "relation": "supports|contradicts|narrows|unlocks"
      }
    ]
  },
  "scene_gates": {
    "S1": {
      "required_fact_ids": [],
      "required_items": [],
      "trust_threshold": null,
      "time_window": null
    },
    "S2": {
      "required_fact_ids": [],
      "required_items": [],
      "trust_threshold": "number|null",
      "time_window": "string|null"
    },
    "S3": {
      "required_fact_ids": [],
      "required_items": [],
      "trust_threshold": null,
      "time_window": null
    },
    "S4": {
      "required_fact_ids": [],
      "required_items": [],
      "trust_threshold": null,
      "time_window": "string|null"
    },
    "S5": {
      "required_fact_ids": ["string"],
      "required_items": ["string"],
      "trust_threshold": "number|null",
      "time_window": null
    }
  },
  "resolution_rules": {
    "recovery_success": {
      "required_fact_ids": ["string"],
      "required_items": ["string"],
      "required_actions": ["string"]
    },
    "accusation_success": {
      "required_fact_ids": ["string"],
      "required_items": ["string"],
      "required_actions": ["string"]
    },
    "soft_fail": {
      "trigger_conditions": ["string"],
      "outcome_flags": ["string"]
    },
    "best_outcome": {
      "required_fact_ids": ["string"],
      "required_items": ["string"],
      "required_actions": ["string"],
      "required_relationship_flags": ["string"]
    }
  },
  "visible_case_slice": {
    "public_room_ids": ["string"],
    "public_object_ids": ["string"],
    "starting_scene_id": "S1",
    "starting_known_fact_ids": ["string"]
  },
  "hidden_case_slice": {
    "private_fact_ids": ["string"],
    "private_overlay_flags": ["string"]
  }
}
```

2) CastRegistry

```json
{
  "elodie": {
    "npc_id": "elodie",
    "display_name": "Élodie Marchand",
    "identity_role": "curator",
    "baseline_traits": ["proud", "precise", "impatient_with_vagueness"],
    "baseline_register": "formal_fr",
    "tell_profile": ["exact_wording", "exact_times"],
    "trust_triggers": ["polite_register", "accurate_summary"],
    "anti_triggers": ["sloppy_accusation"],
    "portrait_config": {
      "base_portrait_id": "elodie_base",
      "state_variants": ["calm", "guarded", "annoyed", "stressed"],
      "card_theme_id": "museum_formal"
    }
  },
  "marc": {
    "npc_id": "marc",
    "display_name": "Marc Dutil",
    "identity_role": "guard",
    "baseline_traits": ["procedural", "tired", "rule_bound"],
    "baseline_register": "direct_protocol_fr",
    "tell_profile": ["procedure_first", "access_gatekeeper"],
    "trust_triggers": ["respectful_tone", "competence"],
    "anti_triggers": ["bypass_process"],
    "portrait_config": {
      "base_portrait_id": "marc_base",
      "state_variants": ["neutral", "procedural", "annoyed", "helpful"],
      "card_theme_id": "security_plain"
    }
  },
  "samira": {
    "npc_id": "samira",
    "display_name": "Samira B.",
    "identity_role": "intern",
    "baseline_traits": ["anxious", "eager", "oversharing"],
    "baseline_register": "simple_fr_with_anglicisms",
    "tell_profile": ["too_many_details_when_nervous"],
    "trust_triggers": ["calm_reassurance"],
    "anti_triggers": ["early_pressure"],
    "portrait_config": {
      "base_portrait_id": "samira_base",
      "state_variants": ["nervous", "helpful", "flustered", "guarded"],
      "card_theme_id": "intern_warm"
    }
  },
  "laurent": {
    "npc_id": "laurent",
    "display_name": "Laurent Vachon",
    "identity_role": "donor",
    "baseline_traits": ["polished", "status_aware", "defensive"],
    "baseline_register": "polished_formal_fr",
    "tell_profile": ["avoids_exact_times"],
    "trust_triggers": ["tact", "formality"],
    "anti_triggers": ["disrespect"],
    "portrait_config": {
      "base_portrait_id": "laurent_base",
      "state_variants": ["amused", "guarded", "defensive", "cold"],
      "card_theme_id": "vip_refined"
    }
  },
  "jo": {
    "npc_id": "jo",
    "display_name": "Jo Leclerc",
    "identity_role": "barista",
    "baseline_traits": ["observant", "casual", "social"],
    "baseline_register": "montreal_casual_fr",
    "tell_profile": ["remembers_clothes_and_vibes"],
    "trust_triggers": ["friendly_specificity"],
    "anti_triggers": ["stiff_interrogation"],
    "portrait_config": {
      "base_portrait_id": "jo_base",
      "state_variants": ["relaxed", "curious", "helpful", "uncertain"],
      "card_theme_id": "cafe_casual"
    }
  }
}
```

3) NPCState

```json
{
  "npc_id": "string",
  "current_room_id": "string",
  "availability": "available|busy|gone|restricted",
  "trust": 0,
  "stress": 0,
  "stance": "helpful|procedural|evasive|defensive|manipulative|flustered",
  "emotion": "calm|stressed|amused|annoyed|nervous|guarded",
  "soft_alignment_hint": "protecting_institution|protecting_self|protecting_someone_else|saving_face|helping_quietly",
  "visible_behavior_flags": ["string"],
  "known_fact_flags": ["string"],
  "belief_flags": ["string"],
  "hidden_flags": ["string"],
  "misremember_flags": ["string"],
  "current_scene_id": "string|null",
  "schedule_state": {
    "current_beat_id": "string|null",
    "next_beat_id": "string|null",
    "last_transition_at": "string|null"
  },
  "card_state": {
    "portrait_variant": "string",
    "tell_cue": "string|null",
    "suggested_interaction_mode": "direct|gentle|formal|procedural|pressure|reassure",
    "trust_trend": "up|flat|down"
  }
}
```

4) DialogueSceneState

```json
{
  "scene_id": "S1|S2|S3|S4|S5",
  "npc_id": "string",
  "allowed_intents": [
    "ask_what_happened",
    "ask_when",
    "ask_where",
    "ask_who",
    "ask_what_seen",
    "request_access",
    "request_permission",
    "present_evidence",
    "challenge_contradiction",
    "summarize_understanding",
    "accuse",
    "reassure",
    "goodbye"
  ],
  "required_slots": [
    {
      "slot_name": "time|location|item|person|reason",
      "required": true
    }
  ],
  "allowed_fact_ids": ["string"],
  "revealed_fact_ids": ["string"],
  "trust_gate": {
    "minimum_value": "number|null",
    "failure_mode": "deny|deflect|delay"
  },
  "stress_gate": {
    "maximum_value": "number|null",
    "failure_mode": "shut_down|evade|switch_register"
  },
  "repair_paths": [
    {
      "repair_id": "string",
      "trigger": "missing_slot|wrong_register|too_aggressive|weak_evidence",
      "response_mode": "sentence_stem|rephrase_choice|meta_hint|alternate_path"
    }
  ],
  "summary_requirement": {
    "required": true,
    "min_fact_count": 1,
    "target_language": "fr"
  },
  "unlock_outputs": {
    "scene_completion_flags": ["string"],
    "new_fact_ids": ["string"],
    "new_object_actions": ["string"],
    "new_scene_ids": ["string"]
  },
  "completion_state": "locked|available|in_progress|completed|failed_soft"
}
```

---

EXECUTION PRIORITIES

You should work in this order unless a task explicitly narrows scope:

Priority 1
- Canonical MBAM Case Bundle
Priority 2
- CastRegistry + seeded role overlays
Priority 3
- Object affordances + evidence/contradiction loop
Priority 4
- Deterministic structured dialogue scenes
Priority 5
- Frontend investigation shell
Priority 6
- French scaffolding + MG1–MG4
Priority 7
- Optional LLM adapter layer
Priority 8
Replay polish and ship validation

---

## IMPLEMENTATION STYLE RULES
- Prefer small, auditable, deterministic increments.
- Do not generalize early unless MBAM implementation clearly benefits.
- Keep mystery truth centralized.
- Add tests with each meaningful backend truth-layer change.
- Preserve replayability and debuggability.
- Be explicit when repo reality forces a spec interpretation choice.
- Surface risks early instead of hiding them.
- If a system is still scaffolded in the repo, extend it only as much as MBAM v1.0 needs.

---

## FIRST-CHAT BEHAVIOR
When starting work in this repo:
1. review the current codebase against this brief
2. review feature spec: docs/enqueteur/case_1_implementation_spec.md
3. identify the exact insertion points for Phase 1 work
4. call out any mismatch between current repo structures and these canonical models
5. review and await for your first task