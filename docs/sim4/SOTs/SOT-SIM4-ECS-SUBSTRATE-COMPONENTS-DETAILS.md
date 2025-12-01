📘 SOT-SIM4-ECS-SUBSTRATE-COMPONENTS-DETAILS
Canonical Agent & World Substrate Components - Implementation Details
Draft 1.0 — Architect-Level, Rust-Aligned, Free-Agent-Spec Compliant

0. Scope & Purpose

This report documents the implemented state of the Sim4 ECS substrate component layer as of Sprint 3 (Sub-sprints 3.1–3.6).

It confirms that:

The concrete Python implementation under backend/sim4/ecs/components/:

Matches the schemas described in SOT-SIM4-ECS-SUBSTRATE-COMPONENTS.

Respects all global constraints in SOP-000/100/200/300 and ECS-related SOTs.

The corresponding tests:

Validate shapes, field wiring, and basic ECS integration.

Provide a minimal but sufficient safety net for later system development and Rust porting.

This appendix is intended to “lock in” the Sim4 substrate schema: any changes after this point require SOT revisions and migration notes.

1. Code Structure & Files

Canonical folder structure implemented:

backend/sim4/ecs/components/
__init__.py

    identity.py
    embodiment.py
    perception.py
    belief.py
    drives.py
    emotion.py
    social.py
    motive_plan.py
    intent_action.py
    narrative_state.py
    inventory.py
    meta.py


Associated tests:

backend/sim4/tests/components/
test_identity_components.py
test_drive_emotion_components.py
test_embodiment_perception_components.py
test_belief_social_components.py
test_motive_plan_components.py
test_intent_inventory_meta_components.py

backend/sim4/tests/
test_ecs_substrate_sanity.py


ecs/components/__init__.py re-exports the canonical dataclasses such that systems and callers can import from a single module:

from ecs.components import (
AgentIdentity,
ProfileTraits,
SelfModelSubstrate,
PersonaSubstrate,
Transform,
Velocity,
RoomPresence,
PathState,
PerceptionSubstrate,
AttentionSlots,
SalienceState,
BeliefGraphSubstrate,
AgentInferenceState,
SocialBeliefWeights,
DriveState,
EmotionFields,
SocialSubstrate,
SocialImpressionState,
FactionAffinityState,
MotiveSubstrate,
PlanStepSubstrate,
PlanLayerSubstrate,
PrimitiveIntent,
SanitizedIntent,
MovementIntent,
InteractionIntent,
ActionState,
NarrativeState,
InventorySubstrate,
ItemState,
DebugFlags,
SystemMarkers,
)


(Exact __init__ contents can be treated as canonical API: future systems should import via this module.)

2. Global Constraints Compliance

Per SOT-SIM4-ECS-SUBSTRATE-COMPONENTS §1 & §16, all components adhere to:

2.1 Substrate-Only, No Semantics

✅ No natural-language strings stored in any component fields.

✅ All semantics are numeric/structural:

Scalars: int, float, bool

Containers: list[...], dict[...], tuple[...]

Optional values: Optional[...]

References are purely EntityID, RoomID, AssetID, ItemID, faction_id: int, topic_id: int, etc.

✅ Any “labels” (e.g. roles, impressions, modes) are stored as enum codes (int) or hashed IDs (int), not strings.

2.2 Rust-Portable Shapes

✅ All components are plain @dataclass types without dynamic attributes or inheritance chains.

✅ No Python-only constructs (lambdas, function refs, arbitrary objects) in fields.

✅ Dict keys are primitive IDs only: EntityID, int, RoomID, etc.

✅ Every dataclass maps 1:1 to a plausible Rust struct:

pub struct DriveState {
pub curiosity: f32,
pub safety_drive: f32,
pub dominance_drive: f32,
pub meaning_drive: f32,
pub attachment_drive: f32,
pub novelty_drive: f32,
pub fatigue: f32,
pub comfort: f32,
}

2.3 No Cross-Layer References

✅ No component imports from runtime/, world/, narrative/, snapshot/, or integration/.

✅ The only non-primitive import is EntityID from ecs/entity.py.

✅ World- and narrative-level state is always referenced indirectly via numeric IDs and handled at higher layers.

2.4 Schema Stability & Versioning

This report declares the Sim4 ECS substrate schema “frozen”:

No renaming existing fields.

No changing field types.

No adding/removing fields without:

Updating SOT-SIM4-ECS-SUBSTRATE-COMPONENTS.

Writing a conceptual migration note (for Python prototype and future Rust port).

3. Per-Module Implementation Details vs SOT

This section maps each implemented module to the corresponding SOT section and confirms field-level alignment.

3.1 identity.py (SOT §4 Identity)

Layer mapping: L3 (identity, self-model) & L7 (persona/aesthetic).

Implemented dataclasses:

AgentIdentity

Fields:

id: EntityID

canonical_name_id: int

role_code: int

generation: int

seed: int

Matches SOT §4.1 exactly.

ProfileTraits

Fields:

introversion: float

volatility: float

conscientiousness: float

agreeableness: float

openness: float

risk_tolerance: float

Matches SOT §4.2.

SelfModelSubstrate

Fields:

identity_vector: list[float]

self_consistency_pressure: float

contradiction_count: int

drift_score: float

Matches SOT §4.3.

PersonaSubstrate

Fields:

style_vector: list[float]

symbol_affinity_vector: list[float]

expressiveness: float

voice_register: float

Matches optional SOT §4.4 (L7 numeric persona).

All identity fields are numeric; vectors are list[float], as allowed.

3.2 embodiment.py (SOT §5 Embodiment)

Layer mapping: L1 (embodiment & raw perception).

ID aliases:

RoomID = int

AssetID = int
(Per SOT guidance; these are pure numeric type aliases.)

Dataclasses:

Transform

room_id: RoomID

x: float

y: float

orientation: float

Matches SOT §5.1, including optional orientation.

Velocity

dx: float

dy: float

Matches SOT §5.2.

RoomPresence

room_id: RoomID

time_in_room: float

Matches SOT §5.3.

PathState

active: bool

waypoints: List[Tuple[float, float]] (waypoints as coordinates)

current_index: int

progress_along_segment: float

path_valid: bool

Matches SOT §5.4 (choosing the “(float, float) waypoints” option).
Range invariants for progress_along_segment (0–1) are explicitly delegated to systems.

3.3 perception.py (SOT §6 Perception & Attention)

Layer mapping: L1/L2.

Imports:

EntityID from ecs/entity.py

RoomID, AssetID from embodiment.py

Dataclasses:

PerceptionSubstrate

visible_agents: List[EntityID]

visible_assets: List[AssetID]

visible_rooms: List[RoomID]

proximity_scores: Dict[EntityID, float]

Matches SOT §6.1.

AttentionSlots

focused_agent: Optional[EntityID]

focused_asset: Optional[AssetID]

focused_room: Optional[RoomID]

secondary_targets: List[EntityID]

distraction_level: float

Matches SOT §6.2.

SalienceState

agent_salience: Dict[EntityID, float]

topic_salience: Dict[int, float]

location_salience: Dict[RoomID, float]

Matches SOT §6.3.

3.4 belief.py (SOT §7 Belief & Concept)

Layer mapping: L3, with a bridge into social beliefs.

Imports:

EntityID from ecs/entity.py

Dataclasses:

BeliefGraphSubstrate

nodes: List[int] — hashed concept IDs.

edges: List[Tuple[int, int]] — pairs of indices into nodes.

weights: List[float]

last_updated_tick: int

source_tags: List[int] | None = None

Matches SOT §7.1; optional source_tags implemented as numeric list.

AgentInferenceState

pending_updates: int

last_inference_tick: int

uncertainty_score: float

epistemic_drift: float

Matches SOT §7.2.

SocialBeliefWeights

perceived_reputation: Dict[EntityID, float]

perceived_status: Dict[EntityID, float]

perceived_alignment: Dict[EntityID, float] (expected −1..+1)

Matches SOT §7.3.

List-length and index invariants (e.g. len(edges) == len(weights); edges indexing into nodes) are left to systems, per SOT.

3.5 drives.py (SOT §8 Drives)

Layer mapping: L4.

Dataclass:

DriveState

curiosity: float

safety_drive: float

dominance_drive: float

meaning_drive: float

attachment_drive: float

novelty_drive: float

fatigue: float (optional in SOT, included here)

comfort: float (optional in SOT, included here)

Matches SOT §8 in full, including optional fatigue/comfort fields.

3.6 emotion.py (SOT §9 Emotion)

Layer mapping: L4.

Dataclass:

EmotionFields

tension: float

mood_valence: float

arousal: float

social_stress: float

excitement: float

boredom: float

Matches SOT §9 exactly.

3.7 social.py (SOT §10 SocialMind)

Layer mapping: L3 + L4 (social beliefs and emotional charge).

Dataclasses:

SocialSubstrate

relationship_to: Dict[EntityID, float] (−1..+1)

trust_to: Dict[EntityID, float] (0–1)

respect_to: Dict[EntityID, float] (0–1)

resentment_to: Dict[EntityID, float] (0–1)

Matches SOT §10.1.

SocialImpressionState

impression_code_to: Dict[EntityID, int] — enum-coded impressions.

misunderstanding_level_to: Dict[EntityID, float]

Matches SOT §10.2.

FactionAffinityState

faction_affinity: Dict[int, float] (−1..+1)

faction_loyalty: Dict[int, float] (0–1)

Matches SOT §10.3.

3.8 motive_plan.py (SOT §11 Motive & Plan)

Layer mapping: L5.

ID aliases:

RoomID = int

AssetID = int

Dataclasses:

MotiveSubstrate

active_motives: List[int] — hashed motive IDs.

motive_strengths: List[float] — same logical length as active_motives.

last_update_tick: int

Matches SOT §11.1; docstring clearly states alignment is enforced by systems.

PlanStepSubstrate

step_id: int

target_agent_id: Optional[EntityID]

target_room_id: Optional[RoomID]

target_asset_id: Optional[AssetID]

status_code: int

Matches SOT §11.2.

PlanLayerSubstrate

steps: List[PlanStepSubstrate]

current_index: int

plan_confidence: float

revision_needed: bool

Matches SOT §11.3.

3.9 intent_action.py (SOT §12 Intent & Action Pipeline)

Layer mapping: L1/L5 bridge.

ID aliases:

RoomID = int

AssetID = int

EntityID from ecs/entity.py

Dataclasses:

PrimitiveIntent

intent_code: int

target_agent_id: Optional[EntityID]

target_room_id: Optional[RoomID]

target_asset_id: Optional[AssetID]

priority: float

Matches SOT §12.1.

SanitizedIntent

intent_code: int

target_agent_id: Optional[EntityID]

target_room_id: Optional[RoomID]

target_asset_id: Optional[AssetID]

priority: float

valid: bool

reason_code: int

Matches SOT §12.2.

MovementIntent

kind_code: int

target_room_id: Optional[RoomID]

target_position: Optional[Tuple[float, float]]

follow_agent_id: Optional[EntityID]

speed_scalar: float

active: bool

Matches SOT §12.3 (with (x, y) coordinates option).

InteractionIntent

kind_code: int

target_agent_id: Optional[EntityID]

target_asset_id: Optional[AssetID]

strength_scalar: float

active: bool

Matches SOT §12.4.

ActionState

mode_code: int

time_in_mode: float

last_mode_change_tick: int

Matches SOT §12.5.

3.10 narrative_state.py (SOT §13 Narrative Handle)

Layer mapping: L6/L7 handle (narrative sidecar).

Dataclass:

NarrativeState

narrative_id: int

last_reflection_tick: int

cached_summary_ref: Optional[int]

tokens_used_recently: int

Matches SOT §13 exactly, including the rule that only the narrative layer may mutate it; ECS systems treat it as read-only.

3.11 inventory.py (SOT §14 Inventory)

Layer mapping: L1 (embodied context).

ID aliases:

RoomID = int

ItemID = int

EntityID from ecs/entity.py

Dataclasses:

InventorySubstrate

items: List[ItemID]

equipped_item_ids: List[ItemID]

Matches SOT §14.1.

ItemState

item_id: ItemID

owner_agent_id: Optional[EntityID]

location_room_id: Optional[RoomID]

status_code: int

Matches SOT §14.2.

3.12 meta.py (SOT §15 Meta / Debug)

Layer mapping: Debug only (no gameplay/narrative semantics).

Dataclasses:

DebugFlags

log_agent: bool

highlight_in_snapshot: bool

freeze_movement: bool

Matches SOT §15.1.

SystemMarkers

archetype_code: int

debug_notes_id: Optional[int]

Matches SOT §15.2.

Docstrings explicitly state this module is for debug/tooling only.

4. Test Coverage & ECS Integration
   4.1 Component-Level Tests

Each component file has a corresponding test module under backend/sim4/tests/components/:

test_identity_components.py

test_drive_emotion_components.py

test_embodiment_perception_components.py

test_belief_social_components.py

test_motive_plan_components.py

test_intent_inventory_meta_components.py

These tests:

Instantiate each dataclass with sample values.

Assert that:

Attributes are set and accessible.

Lists and dicts are stored as-is.

Optional fields accept None as expected.

For components with list alignment notes (e.g. MotiveSubstrate, BeliefGraphSubstrate), tests explicitly document that alignment is a system responsibility, not enforced at the dataclass level.

4.2 ECS Substrate Sanity Test (Sub-sprint 3.6)

File: backend/sim4/tests/test_ecs_substrate_sanity.py

Scenario:

Test 1 — Simple Entity Bundle

Use ECSWorld and substrate components:

AgentIdentity

Transform

EmotionFields

Create a single entity with this component bundle.

Query for (AgentIdentity, Transform, EmotionFields):

Expect exactly one result.

Assert values match the ones used at creation.

Test 2 — Multiple Entities, Mixed Components

Create 2–3 entities with different component combinations:

Some with DriveState, some without.

Query on (DriveState,) only:

Assert only the entities with DriveState are returned.

Test 3 — Command + Component Interaction (optional but present)

Use ECSCommandBuffer and ECSWorld.apply_commands() to:

Modify a field on DriveState or EmotionFields via SET_FIELD.

Query again and assert that the numeric changes are visible.

Purpose:

Demonstrates that substrate components:

Are compatible with ECSWorld’s archetype storage.

Work with standard query signatures.

Support deterministic command application (SET_COMPONENT, SET_FIELD).

All tests pass under pytest, confirming basic integration between:

Component schemas

ECS core

Commands & queries

5. Determinism & Rust Portability Considerations
   5.1 Determinism

The components themselves are passive:

They do not:

Generate random values.

Consult external state.

Deterministic behavior is entirely in:

ECSWorld operations (per SOT-ECS-CORE).

Systems (per SOT-ECS-SYSTEMS).

Command sequencing (per SOT-ECS-COMMANDS-AND-EVENTS).

Because fields are:

Simple values (ints, floats, bools),

Deterministic collections (list, dict with primitive keys),
their presence does not introduce any non-determinism.

5.2 Rust Portability

All components map directly to Rust structs backed by:

Vec<T> for lists

HashMap<K, V> (or equivalent) for dicts

Primitive scalars for numeric fields

No field type requires Python-specific machinery to port.

ID aliases (RoomID, AssetID, ItemID, etc.) are all int and can be mapped to:

pub type RoomId = i32;
pub type AssetId = i32;
pub type ItemId = i32;
pub type EntityId = i32;


or similar, without changing semantics.

6. Extension & Freeze Guidelines

To keep the substrate consistent across Sim4 and future SimX/Rust ports:

Schema Freeze (Sim4)

Treat all current fields as locked for Sim4.

Any change to:

Field names

Field types

Presence/absence of fields
must go through:

SOT-SIM4-ECS-SUBSTRATE-COMPONENTS update.

A short migration note (e.g. “v1 → v2” diff for each affected component).

Adding New Components

New substrate components should:

Live under ecs/components/.

Follow the same numeric-only rules.

Be added to:

SOT-SIM4-ECS-SUBSTRATE-COMPONENTS (new section).

ecs/components/__init__.py for re-export.

A dedicated test module under backend/sim4/tests/components/.

Centralizing ID Aliases (Future SimX)

Current implementation defines ID aliases in several modules:

RoomID, AssetID in embodiment.py

RoomID, ItemID in inventory.py

RoomID, AssetID in intent_action.py, motive_plan.py

This is acceptable for Sim4 (all aliases are int), but for SimX/Rust:

A future SOT revision may introduce a central types module.

Any such change must preserve the numeric identity semantics.

7. Completion Statement

As of Sprint 3 (Sub-sprints 3.1–3.6), the following is true:

ecs/components/ matches the layout specified in SOT-SIM4-ECS-SUBSTRATE-COMPONENTS §2.

Every dataclass defined in the SOT:

Exists in code under the expected module.

Uses only Rust-portable, numeric/structural fields.

Contains no natural-language text.

Has a clear mapping to the 7-layer mind and Free Agent Spec.

ECS core, systems, and command semantics:

Can safely rely on these component shapes as stable substrate.

Have validated interoperability via test_ecs_substrate_sanity.py.

Therefore:

The Sim4 ECS substrate component layer is implemented, verified, and locked per SOT-SIM4-ECS-SUBSTRATE-COMPONENTS and related ECS SOTs.
Subsequent architects may treat these schemas as canonical for Sim4 and build systems, runtime, world, and narrative layers on top without further schema changes, unless accompanied by a formal SOT revision.