📘 SOT-SIM4-ECS-SUBSTRATE-COMPONENTS
Canonical Agent & World Substrate Components
Draft 1.0 — Architect-Level, Rust-Aligned, Free-Agent-Spec Compliant

0. Scope & Purpose

This SOT defines the canonical ECS component set for Sim4:

Which components live under ecs/components/.

How they map to:

the 7-layer agent mind (SOP-300), and

the Free Agent Spec (SelfModel, ConceptGraph, DriveState, SocialMind, etc.).

What fields they expose at shape-level (no code, but the data architecture).

What global rules they must obey for:

determinism (SOP-200),

layer purity (SOP-100),

substrate-only cognition (SOP-300),

Rust portability (SOT-ECS-CORE).

This SOT replaces the earlier “SOT-SIM4-ECS-COMPONENTS” and is aligned with:

SOT-SIM4-ENGINE

SOT-SIM4-ECS-CORE

SOT-SIM4-RUNTIME-TICK

Locked SOPs: SOP-000, 100, 200, 300.

1. Global Rules for All Components

All ECS substrate components must obey these global constraints:

1.1 Substrate-Only, No Semantics

Components store numeric / structural data only:

ints, floats, booleans

fixed-length vectors/tuples

enums as ints

lists with stable ordering

small, fixed-shape dataclasses.

No free-form natural language:

no raw dialog text,

no “labels” like "angry", "mentor", "enemy" as strings.

Semantic meaning is always in narrative/ and external stores.

1.2 Rust-Portable Shapes

Allowed:

Plain dataclasses with primitive fields and lists.

Enums implemented as ints.

Dicts keyed by primitive IDs (EntityID, RoomID, small int codes).

Forbidden:

Arbitrary Python objects.

Lambdas, closures, function refs.

Runtime attribute injection / dynamic schema changes.

1.3 No Cross-Layer References

Components must not hold:

references to runtime, world subsystems, narrative objects,

file handles, sockets, or other IO resources.

All external references are by ID only:

EntityID, RoomID, AssetID, DoorID, FactionID, ItemID, etc.

1.4 Stable Schema & Versioning

Once stable, a component’s fields are frozen for a Sim4 release.

Any changes require:

SOT revision,

migration plan (even if only conceptual for the prototype),

explicit notes on compatibility.

1.5 Clear Layer Mapping

Each component must be clearly mapped to one or more layers:

L1 — Embodied & Raw Perception
L2 — Perception & Attention
L3 — Belief, Concept & Self-Model
L4 — Drives & Emotion Fields
L5 — Motives & Planning
L6 — Reflection (semantic only, narrative)
L7 — Narrative & Persona/Aesthetic Mind


If a component spans multiple layers (e.g. social + emotional), that must be explicit.

2. Folder Layout under ecs/components/

Canonical Sim4 layout:

ecs/components/
__init__.py

identity.py        # AgentIdentity, ProfileTraits, SelfModelSubstrate
embodiment.py      # Transform, Velocity, RoomPresence, PathState
perception.py      # PerceptionSubstrate, Attention/Salience
belief.py          # BeliefGraphSubstrate, AgentInferenceState, SocialBeliefWeights
drives.py          # DriveState (curiosity, safety, attachment, etc.)
emotion.py         # EmotionFields (tension, mood, arousal, etc.)
social.py          # SocialSubstrate: relationships, trust, factions
motive_plan.py     # MotiveSubstrate, PlanLayerSubstrate
intent_action.py   # PrimitiveIntent, SanitizedIntent, MovementIntent,
# InteractionIntent, ActionState
narrative_state.py # NarrativeState (LLM-owned semantic handle)
inventory.py       # InventorySubstrate, item references
meta.py            # Debug flags, SystemMarkers, Tags


Potential future extension:

persona.py — L7 aesthetic vectors (may be folded into identity.py for Sim4 if needed).

3. Mapping to 7-Layer Mind & Free Agent Spec
   3.1 Mind Layers

L1 — Embodied & Raw Perception

embodiment.py, lower-level parts of perception.py, inventory.py.

L2 — Perception & Attention

perception.py (salience, attention slots).

L3 — Belief, Concept & Self-Model

identity.py (SelfModelSubstrate),

belief.py (BeliefGraphSubstrate),

social.py (beliefs about others),

parts of persona/aesthetic (if numeric).

L4 — Drives & Emotion Fields

drives.py, emotion.py,

social emotional charge in social.py.

L5 — Motives & Planning

motive_plan.py,

intent bridge in intent_action.py.

L6 — Reflection (semantic only)

semantic, in narrative/ (no ECS substrate).

L7 — Narrative & Persona/Aesthetic

numeric persona vectors (in identity.py or future persona.py),

narrative_state.py for semantic handles.

3.2 Free Agent Spec Mapping

SelfModel → SelfModelSubstrate (identity.py).

ConceptGraph / BeliefState → BeliefGraphSubstrate, AgentInferenceState (belief.py).

DriveState → DriveState (drives.py).

MotiveSystem / PlanLayer → MotiveSubstrate, PlanLayerSubstrate (motive_plan.py).

ReflectionState → semantic, narrative/ + NarrativeState handle (narrative_state.py).

SocialMind → SocialSubstrate (social.py) + SocialBeliefWeights (belief.py bridge).

AestheticMind → numeric persona vectors (identity/persona), plus semantic aesthetic in narrative/.

4. Identity Components (identity.py)

Purpose: anchor agents, personality, and self-model vector substrate.

4.1 AgentIdentity

Fields (shape-level):

id: EntityID — stable entity identifier.

canonical_name_id: int — hashed name, not free text.

role_code: int — enum code (worker, supervisor, visitor, etc.).

generation: int — SimX-style generational index.

seed: int — per-agent RNG seed base (if used).

Layer: L3 (self anchor) + infra.

4.2 ProfileTraits

Stable personality traits / tendencies:

introversion: float

volatility: float

conscientiousness: float

agreeableness: float

openness: float

risk_tolerance: float

optional variants (e.g. warmth, assertiveness) as needed.

Layer: L3 / L4 predisposition substrate.

4.3 SelfModelSubstrate

Numeric substrate for identity coherence and drift:

identity_vector: list[float]
Small fixed-length vector (e.g. 8–32 dims).

self_consistency_pressure: float
Pressure to keep identity_vector close to baseline.

contradiction_count: int

drift_score: float
Distance from initial vector / baseline.

Layer: L3.
Narrative interprets this as self-doubt, identity shifts, “character growth”.

4.4 (Optional) PersonaSubstrate (L7 numeric)

If present (either here or in persona.py):

style_vector: list[float] — aesthetic style prefs (industrial/cozy/etc., encoded as dims).

symbol_affinity_vector: list[float] — attachment to symbolic motifs.

expressiveness: float

voice_register: float

Layer: L7 numeric. No semantics; narrative uses it to color voice and choices.

5. Embodiment Components (embodiment.py)

Purpose: physical presence of agents in the world.

5.1 Transform

room_id: RoomID

x: float

y: float

optionally orientation: float (angle).

5.2 Velocity

dx: float

dy: float

5.3 RoomPresence

room_id: RoomID

time_in_room: float — accumulated since entry (seconds).

5.4 PathState

active: bool

waypoints: list[(float, float)] or list of node IDs.

current_index: int

progress_along_segment: float (0–1).

path_valid: bool — invalid if blocked/unreachable.

Layer: L1 embodiment substrate.

6. Perception Components (perception.py)

Purpose: raw perception + attention structures (no semantics).

6.1 PerceptionSubstrate

visible_agents: list[EntityID]

visible_assets: list[AssetID]

visible_rooms: list[RoomID] — adjacent or line-of-sight rooms.

proximity_scores: dict[EntityID, float] — 0–1 normalized closeness.

6.2 AttentionSlots

focused_agent: Optional[EntityID]

focused_asset: Optional[AssetID]

focused_room: Optional[RoomID]

secondary_targets: list[EntityID]

distraction_level: float — 0–1.

6.3 SalienceState

agent_salience: dict[EntityID, float]

topic_salience: dict[int, float] — hashed topic IDs (from ConceptGraph).

location_salience: dict[RoomID, float]

Layers: L1/L2 substrate.

7. Belief Components (belief.py)

Purpose: ConceptGraph + belief confidence; includes a bridge to social beliefs.

7.1 BeliefGraphSubstrate

nodes: list[int] — hashed concept/belief IDs.

edges: list[(int, int)] — pairs of indices into nodes.

weights: list[float] — confidence/strength per edge.

last_updated_tick: int

Optional:

source_tags: list[int] — short enums (self, other, rumor, world).

7.2 AgentInferenceState

pending_updates: int

last_inference_tick: int

uncertainty_score: float

epistemic_drift: float — how much the belief graph changed recently.

7.3 SocialBeliefWeights

Bridge between beliefs and social substrate:

perceived_reputation: dict[EntityID, float]

perceived_status: dict[EntityID, float]

perceived_alignment: dict[EntityID, float] — -1..1 (opponent ↔ ally).

Layer: L3 (beliefs) with social hooks (feeds L4/L5).

8. Drive Components (drives.py)

Purpose: numeric drive vector that fuels motives.

8.1 DriveState

Example fields (Sim4 baseline):

curiosity: float

safety_drive: float

dominance_drive: float

meaning_drive: float

attachment_drive: float

novelty_drive: float

Optional:

fatigue: float

comfort: float

Ranges must be defined & enforced by systems (e.g. 0–1 with clamping).

Layer: L4.

9. Emotion Components (emotion.py)

Purpose: continuous emotion fields, no labels.

9.1 EmotionFields

tension: float

mood_valence: float — e.g. -1..+1.

arousal: float

social_stress: float

excitement: float

boredom: float

Layer: L4 substrate.
Narrative maps this to “anxious”, “calm”, etc. — but ECS never stores those words.

10. Social Components (social.py)

Purpose: numeric SocialMind substrate — affinities, trust, factions.

10.1 SocialSubstrate

Could be split into multiple dataclasses; conceptually:

relationship_to: dict[EntityID, float]
-1..+1 overall affinity.

trust_to: dict[EntityID, float]
0–1 trust.

respect_to: dict[EntityID, float]
0–1 admiration.

resentment_to: dict[EntityID, float]
0–1 grudges.

10.2 SocialImpressionState

impression_code_to: dict[EntityID, int]
Enum-coded impressions (“mentor”, “rival”, etc.) as ints, not strings.

misunderstanding_level_to: dict[EntityID, float]
How misunderstood this agent feels in relation to others (0–1).

10.3 FactionAffinityState

faction_affinity: dict[int, float] — faction ID → [-1, +1].

faction_loyalty: dict[int, float] — faction ID → [0, 1].

Layers: L3 (beliefs about others) + L4 (emotional charge).

11. Motive & Plan Components (motive_plan.py)

Purpose: numeric representation of drives → motives → plans.

11.1 MotiveSubstrate

active_motives: list[int]
Hashed motive IDs (e.g. “repair_relationship_X” encoded as an int).

motive_strengths: list[float]
One strength per motive.

last_update_tick: int

No natural language motive text; only hashed codes.

11.2 PlanStepSubstrate (conceptual step struct)

step_id: int — hashed step code.

target_agent_id: Optional[EntityID]

target_room_id: Optional[RoomID]

target_asset_id: Optional[AssetID]

status_code: int — enum: PENDING, IN_PROGRESS, DONE, FAILED.

11.3 PlanLayerSubstrate

steps: list[PlanStepSubstrate]

current_index: int

plan_confidence: float

revision_needed: bool

Layer: L5 substrate (planning structure).

12. Intent & Action Pipeline (intent_action.py)

Purpose: deterministic pipeline from motives to movement & interaction.

12.1 PrimitiveIntent

Input substrate for external/narrative/player suggestions:

intent_code: int — hashed “want_to_X” ID.

target_agent_id: Optional[EntityID]

target_room_id: Optional[RoomID]

target_asset_id: Optional[AssetID]

priority: float

12.2 SanitizedIntent

Output of deterministic gating:

Same fields as PrimitiveIntent, plus:

valid: bool

reason_code: int — enum-coded reason if invalid.

12.3 MovementIntent

kind_code: int — WALK_TO_ROOM, FOLLOW_AGENT, etc.

target_room_id: Optional[RoomID]

target_position: Optional[(float, float)]

follow_agent_id: Optional[EntityID]

speed_scalar: float

active: bool

12.4 InteractionIntent

kind_code: int — TALK, INSPECT, PICK_UP, USE, etc.

target_agent_id: Optional[EntityID]

target_asset_id: Optional[AssetID]

strength_scalar: float

active: bool

12.5 ActionState

mode_code: int — IDLE, WALKING, TALKING, INTERACTING, WAITING, STUCK.

time_in_mode: float

last_mode_change_tick: int

Layers: L1/L5 bridge (from plan to embodied actions).

13. Narrative State Components (narrative_state.py)

Purpose: ECS-resident handle for LLM narrative/reflective state.
Narrative may write here; ECS systems must not.

13.1 NarrativeState

narrative_id: int — hashed identifier for an ongoing “arc”.

last_reflection_tick: int

cached_summary_ref: Optional[int]
ID into external semantic store (e.g. vector DB, text log).

tokens_used_recently: int — for budgeting/throttling.

Rules:

Only narrative layer (via adapters) may mutate this.

ECS systems treat it as read-only metadata, if at all.

(If we keep a separate ReflectionState, it follows the same rule; can be included here or as another dataclass in this module.)

Layer: L6/L7 semantic handle.

14. Inventory Components (inventory.py)

Purpose: items/tools as part of agent context.

14.1 InventorySubstrate

items: list[ItemID]

equipped_item_ids: list[ItemID]

14.2 ItemState

item_id: ItemID

owner_agent_id: Optional[EntityID]

location_room_id: Optional[RoomID]

status_code: int — enum: IN_INVENTORY, IN_WORLD, EQUIPPED, etc.

Layer: primarily L1 (embodied context).
Narrative can interpret items symbolically, but ECS just tracks them structurally.

15. Meta / Debug Components (meta.py)

Purpose: debugging, tagging, and tooling — not gameplay or narrative.

15.1 DebugFlags

log_agent: bool

highlight_in_snapshot: bool

freeze_movement: bool

15.2 SystemMarkers

archetype_code: int — small enum / int for archetype/debug classification.

debug_notes_id: Optional[int] — hash key to external debug text store.

Rules:

Ignored by narrative/world logic.

Used only by debug tooling, visualization, test harnesses.

16. Constraints & Enforcement

The architect and any dev agent must ensure:

No semantics creep:

If a field starts looking like language (“emotion_label”, “dialog_text”), it belongs in narrative/, not ECS substrate.

Numeric-only mind:

Social and emotional states are numbers and enums, not words.

Strict ownership for NarrativeState:

Only narrative/ writes to narrative_state.py components.

Stable enums:

All enum fields (mode_code, role_code, kind_code, etc.) must map to a central registry (doc or module) to keep Rust migration trivial.

Layer separation:

Body/world-inventory data (L1) must not smuggle in L6/L7 semantics.

17. Completion Condition for SOT-SIM4-ECS-SUBSTRATE-COMPONENTS

This SOT is considered implemented and respected when:

ecs/components/ matches the file layout specified here.

Each component dataclass:

uses only Rust-portable types,

has no natural-language fields,

has a clear mapping to the 7-layer mind and Free Agent Spec.

ECS systems (per SOT-ECS-SYSTEMS):

operate exclusively on these components,

treat them as numeric/structural substrate,

never write to NarrativeState (only narrative does).

The component set is sufficient to:

implement all substrate flows in SOP-300,

support Sim4’s systems and SimX’s long-arc agent evolution without schema collapse.

Once those conditions hold, the ECS substrate layer is locked:
a clean, deterministic numeric mind on which Loopforge’s semantic narrative can safely dance.