# 📘 SOT-SIM4-SNAPSHOT-AND-EPISODE
_**WorldSnapshot, AgentSnapshot & StageEpisodeV2**_  
**Draft 1.0 — Architect-Level, SOP-100/200/300 Compliant**

---

## 0. Scope & Purpose
This SOT defines the **snapshot layer** for Sim4:
* The **read-only data types** used to represent:
  * the **current world state** (`WorldSnapshot`, `RoomSnapshot`, `AgentSnapshot`, etc.), and
  * the **UI-facing episode structure** (`StageEpisodeV2` and friends).
* Where the **snapshot builders** live and what they consume:
  * `world_snapshot_builder.py`
  * `episode_builder.py`
* How snapshots:
  * are derived from **ECSWorld + WorldContext**,
  * are fed to **runtime history**, **narrative**, and **frontend**,
  * remain deterministic, Rust-portable, and layer-pure.

This SOT answers:
* What exactly is in a `WorldSnapshot` and `AgentSnapshot`.
* What exactly is in `StageEpisodeV2` and related episode types.
* How snapshot and episode builders interact with:
  * ECS (SOT-SIM4-ECS-CORE / SUBSTRATE / SYSTEMS),
  * world engine (SOT-SIM4-WORLD-ENGINE), 
  * runtime tick & narrative (SOT-SIM4-RUNTIME-TICK, SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT, SOT-SIM4-NARRATIVE-INTERFACE).

It does **not** define:
* Simulation logic (that lives in ECS systems & world engine).
* Narrative logic or text generation.
* UI rendering code (frontend).

This document is the **single source of truth** for the snapshot layer and episode types.

---

## Sprint 7 — Status (Implemented)

As of Sprint 7 completion:

- Snapshot DTOs implemented:
  - WorldSnapshot, RoomSnapshot, AgentSnapshot, ItemSnapshot, TransformSnapshot.
- Episode DTOs implemented:
  - EpisodeMeta, EpisodeMood, TensionSample, SceneSnapshot, DayWithScenes, EpisodeNarrativeFragment, StageEpisodeV2.
- Builders implemented (minimal, deterministic, read-only):
  - world_snapshot_builder.build_world_snapshot(WorldContext, ECSWorld → WorldSnapshot).
  - episode_builder.start_new_episode / append_tick_to_episode / finalize_episode (bookkeeping only; no narrative logic).
- Diff layer implemented (minimal, narrative/UI-friendly):
  - SnapshotDiff, AgentDiff, RoomOccupancyDiff, ItemDiff DTOs.
  - compute_snapshot_diff(prev, curr) and summarize_diff_for_narrative(diff) helpers.
- Package surface: backend.sim4.snapshot exports DTOs, builders, and diff helpers for runtime and narrative consumption.

Deferred to Sprint 8+:
- Episode mood aggregation, scene segmentation, tension curves.
- Advanced agent identity/persona/drive population in snapshots.
- Runtime wiring for history/diff and NarrativeTickContext invocation.

## 1. Position in the 6-Layer DAG
DAG reminder:
```text
Kernel:   runtime → ecs → world
                \         \
                 \         → snapshot → integration
                  \
                   → (read-only views) → narrative
narrative → (suggestion queues) → runtime (Phase A integration ONLY)
```

Within this DAG:
* snapshot/ is a **pure view layer**:
  * It **reads** ECS and world state (`WorldContext`, `ECSWorld`).
  * It **exposes** read-only DTOs to:
    * runtime (history, narrative context),
    * narrative (via interface),
    * frontend (via integration API).

Constraints:
* `snapshot/` must **not**:
  * import `runtime/`,
  * import `narrative/`,
  * perform simulation logic or modify ECS/world.
* `snapshot/` may import:
  * ECS component types (for shaping `AgentSnapshot`),
  * world identity types (RoomID, WorldIdentity, etc.),
  * episode type enums (e.g. `EpisodeMood`).

---

## 2. Folder Layout

Canonical structure:
```text
snapshot/
    world_snapshot.py      # WorldSnapshot, RoomSnapshot, AgentSnapshot, ItemSnapshot, etc.
    episode_types.py       # StageEpisodeV2, EpisodeMeta, EpisodeMood, DayWithScenes, Scene, etc.
    diff_types.py          # (optional) SnapshotDiff, EventSummary types
    world_snapshot_builder.py  # build_world_snapshot(...)
    episode_builder.py         # build_stage_episode(...), append_tick_to_episode(...)
```
* `world_snapshot.py` and `episode_types.py` contain **plain dataclasses and enums only**.
* `world_snapshot_builder.py` and `episode_builder.py` contain **pure functions** that:
  * read `WorldContext` + `ECSWorld`,
  * construct snapshots / episodes,
  * perform **no mutations**.

---

## 3. Design Principles
### 3.1 Read-only DTOs
All types in `snapshot/` are:
* **Immutable in spirit:** treated as read-only after construction.
* Pure data carriers:
  * ints, floats, bools,
  * strings (labels for UI),
  * lists/tuples,
  * small enums and nested dataclasses.
* No back-references to engine objects:
  * No `ECSWorld`, `WorldContext`, or system handles inside snapshots.
  * Only IDs and materialized fields.

### 3.2 Determinism
Given:
* initial state,
* the sequence of ECS/world mutations,
* the tick index,

`world_snapshot_builder` and `episode_builder` must produce **identical snapshots and episodes** across runs.

Rules:
* No OS time or random calls inside builders.
* No reliance on dict/set iteration order without explicit sorting.
* Entity and room lists must have **stable ordering** (e.g., by ID).

---

### 3.3 Rust Portability
All snapshot and episode types must:
* map cleanly to Rust structs with `Vec`s and enums,
* avoid Python-only features (dynamic attributes, subclassing gymnastics).

We treat them as canonical **cross-language schemas**.

---

## 4. World Snapshot Schema (`world_snapshot.py`)
Sim4 snapshots follow a 3-layer conceptual split (aligned with earlier Sim3 docs):
* Identity Layer (static-ish)
* Runtime Layer (mutable state)
* Snapshot Layer (this SOT’s types)

---

### 4.1 Core Types
#### 4.1.1 WorldSnapshot
Shape-level:
```python
@dataclass(frozen=True)
class WorldSnapshot:
    world_id: int
    tick_index: int
    episode_id: int
    time_seconds: float

    rooms: list["RoomSnapshot"]
    agents: list["AgentSnapshot"]
    items: list["ItemSnapshot"]

    # Optional aggregated metrics, maps by ID:
    room_index: dict[int, int]      # room_id -> index in rooms
    agent_index: dict[int, int]     # agent_id -> index in agents
```

Notes:
* `world_id`, `room_id`, `agent_id`, `item_id` are small int IDs, mapping back to world/ECS identity.
* `room_index` / `agent_index` are convenience lookups; builders must fill them deterministically or omit if not needed.

---

#### 4.1.2 RoomSnapshot
```python
@dataclass(frozen=True)
class RoomSnapshot:
    room_id: int
    label: str              # UI name (not used for substrate)
    kind_code: int          # enum-coded room kind

    occupants: list[int]    # agent_ids
    items: list[int]        # item_ids

    neighbors: list[int]    # room_ids

    # Optional display metadata:
    tension_tier: str       # "low", "medium", "high", "critical"
    highlight: bool
```

* `label` and `tension_tier` are for **UI & narrative**; substrate ignores them.
* `kind_code` is numeric and must match a documented enum registry.

---

#### 4.1.3 AgentSnapshot
This is the main bridge between **substrate** and **semantic consumers** (narrative, UI).
```python
@dataclass(frozen=True)
class AgentSnapshot:
    agent_id: int
    room_id: int | None

    # Identity / persona
    role_code: int                 # from AgentIdentity
    generation: int                # from AgentIdentity
    profile_traits: dict[str, float]   # subset from ProfileTraits
    identity_vector: list[float]   # from SelfModelSubstrate (optional subset)
    persona_style_vector: list[float] | None  # if present in substrate

    # Drives & emotion
    drives: dict[str, float]       # e.g. {"curiosity": 0.7, "safety": 0.3}
    emotions: dict[str, float]     # e.g. {"tension": 0.4, "mood_valence": -0.2}

    # Social
    key_relationships: list["AgentSocialSnapshot"]

    # Motives & plans
    active_motives: list["MotiveSnapshot"]
    plan: "PlanSnapshot" | None

    # Action / movement
    transform: "TransformSnapshot"
    action_state_code: int         # mirrored from ActionState.mode_code

    # Narrative hooks
    narrative_state_ref: int | None   # from NarrativeState.narrative_id
    cached_summary_ref: int | None    # from NarrativeState.cached_summary_ref
```

Helper types:
```python
@dataclass(frozen=True)
class AgentSocialSnapshot:
    other_agent_id: int
    relationship: float    # -1..+1
    trust: float           # 0..1
    respect: float         # 0..1
    resentment: float      # 0..1
    impression_code: int   # short enum, if available
```
```python
@dataclass(frozen=True)
class MotiveSnapshot:
    motive_id: int         # hashed motive ID
    strength: float
```
```python
@dataclass(frozen=True)
class PlanStepSnapshot:
    step_id: int
    target_agent_id: int | None
    target_room_id: int | None
    target_asset_id: int | None
    status_code: int       # PENDING, IN_PROGRESS, DONE, FAILED
```
```python
@dataclass(frozen=True)
class PlanSnapshot:
    steps: list[PlanStepSnapshot]
    current_index: int
    confidence: float
```
```python
@dataclass(frozen=True)
class TransformSnapshot:
    room_id: int | None
    x: float
    y: float
```

Mapping to components (for builders):
* From `identity.py`: `AgentIdentity`, `ProfileTraits`, `SelfModelSubstrate`, persona substrate.
* From `drives.py`: `DriveState`.
* From `emotion.py`: `EmotionFields`.
* From `social.py` + `belief.py`: pick a **subset** of relationships for `key_relationships` (e.g., top N by |relationship| or salience).
* From `motive_plan.py`: `MotiveSubstrate`, `PlanLayerSubstrate`.
* From `intent_action.py`: `ActionState`, `PrimitiveIntent` (if we want to surface).
* From `embodiment.py`: `Transform`, `RoomPresence`.
* From `narrative_state.py`: `NarrativeState`.

Builders decide **how much of the full substrate** to reflect; SOT just fixes the shape.

---

#### 4.1.4 ItemSnapshot
```python
@dataclass(frozen=True)
class ItemSnapshot:
    item_id: int
    room_id: int | None
    owner_agent_id: int | None
    status_code: int            # IN_WORLD, IN_INVENTORY, EQUIPPED, ...
    label: str                  # UI name, not used by substrate
```

---

## 5. Episode Schema (`episode_types.py`)
This is the Sim4 version of the StageEpisodeV2 spec (backwards compatible with existing Era III concepts where possible).

---

### 5.1 EpisodeMeta
```python
@dataclass(frozen=True)
class EpisodeMeta:
    episode_id: int
    title: str
    synopsis: str

    tick_start: int
    tick_end: int
    duration_seconds: float

    created_at_ms: int          # optional, for UI; not used for determinism
```

---

### 5.2 EpisodeMood
Numeric mood + short labels, for UI ribbons.
```python
@dataclass(frozen=True)
class EpisodeMood:
    # Numeric fields
    tension_avg: float
    tension_peak: float
    sentiment_valence: float   # -1..+1
    social_cohesion: float     # 0..1

    # Optional semantic labels (UI only)
    summary_label: str         # e.g. "rising tension"
```

---

### 5.3 Day / Scene Structures
We keep the day/scene structure as the frontend-facing unit.
```python
@dataclass(frozen=True)
class SceneSnapshot:
    scene_id: int
    label: str

    tick_start: int
    tick_end: int

    focus_room_id: int | None
    focus_agent_ids: list[int]

    tension_curve: list["TensionSample"]
```
```python
@dataclass(frozen=True)
class TensionSample:
    tick_index: int
    tension: float
```
```python
@dataclass(frozen=True)
class DayWithScenes:
    day_index: int
    label: str
    scenes: list[SceneSnapshot]
```
---

### 5.4 StageEpisodeV2
Final UI-facing episode object:
```python
@dataclass(frozen=True)
class StageEpisodeV2:
    meta: EpisodeMeta
    mood: EpisodeMood

    # Structural Layout
    days: list[DayWithScenes]

    # World views
    key_world_snapshots: list[WorldSnapshot]    # selected “frames”
    key_agent_timelines: dict[int, list[WorldSnapshot]]  # optional

    # Narrative overlays
    narrative_fragments: list["EpisodeNarrativeFragment"]
```
```python
@dataclass(frozen=True)
class EpisodeNarrativeFragment:
    tick_index: int
    agent_id: int | None
    room_id: int | None
    text: str
    importance: float
```

Notes:
* `key_world_snapshots` can be a sparse selection of snapshots (e.g., one per scene or per key moment), not every tick.
* `key_agent_timelines` is optional and may be omitted or minimal for Sim4; SOT sets the shape.

---

## 6. Snapshot & Episode Builders
### 6.1 world_snapshot_builder.py
Entry points:
```python
def build_world_snapshot(
    tick_index: int,
    episode_id: int,
    world_ctx: "WorldContext",
    ecs_world: "ECSWorld",
) -> WorldSnapshot: ...
```

Responsibilities:
1. Read:
   * `WorldContext` for:
     * world time,
     * room graph and static metadata,
     * item placements (if world-side).
   * `ECSWorld` for:
     * agent components (identity, drives, emotions, social, motives, plans, etc.),
     * agent presence and transforms,
     * inventory state.
2. Iterate entities in **deterministic order** (e.g., by `EntityID`).
3. Construct:
   * `RoomSnapshot` list, sorted by `room_id`.
   * `AgentSnapshot` list, sorted by `agent_id`.
   * `ItemSnapshot` list, sorted by `item_id`.
4. Return a fully populated `WorldSnapshot`.

Constraints:
* No ECS/world mutations.
* No calls to narrative.
* No I/O.

### 6.1.1 Snapshot Diffs (Implemented in Sprint 7)

The snapshot layer includes a minimal, deterministic diff facility for narrative/UI hooks:

- Types: `SnapshotDiff`, `AgentDiff`, `RoomOccupancyDiff`, `ItemDiff` (frozen, primitives-only DTOs).
- Builder: `compute_snapshot_diff(prev: WorldSnapshot, curr: WorldSnapshot) -> SnapshotDiff`.
  - Detects agent room changes and position changes, room entries/exits, and item spawn/despawn/moves.
  - Pure transformation over snapshots; no imports from ECS/world/runtime/narrative; explicit sorting for determinism.
- Summarization: `summarize_diff_for_narrative(diff: SnapshotDiff) -> dict`.
  - Produces a compact JSON-like dict for `NarrativeTickContext.diff_summary`.
  - Keys: `moved_agents`, `room_entries`, `room_exits`, `spawned_items`, `despawned_items`.

---

### 6.2 `episode_builder.py`

Entry points:

def start_new_episode(
episode_id: int,
initial_snapshot: WorldSnapshot,
) -> StageEpisodeV2: ...

def append_tick_to_episode(
episode: StageEpisodeV2,
tick_index: int,
world_snapshot: WorldSnapshot,
events: list["WorldEvent"],
narrative_fragments: list["StoryFragment"],
) -> StageEpisodeV2: ...

def finalize_episode(
episode: StageEpisodeV2,
) -> StageEpisodeV2: ...


Responsibilities:

start_new_episode:

Initialize EpisodeMeta:

tick_start, provisional title/synopsis placeholders.

Seed days and key_world_snapshots with first snapshot.

append_tick_to_episode:

Update episode-level stats:

track tension samples from agents/rooms (aggregated),

track new scenes/days if tick crosses boundaries (e.g. time-of-day).

Append WorldSnapshot to key_world_snapshots only if it is:

structurally meaningful (scene boundary, key event),

or meets a sampling policy (every N ticks).

Integrate StoryFragments (from runtime narrative context Phase I) into EpisodeNarrativeFragments.

finalize_episode:

Compute EpisodeMood from accumulated tension/social metrics.

Finalize DayWithScenes structure:

segment tick range into scenes based on tension or configured markers.

Fill in meta.synopsis and meta.title using:

numeric stats,

or narrative-provided summary (if available) via NarrativeEpisodeOutput.

Constraints:

episode_builder may be called by runtime after tick F/G/H.

It may read narrative outputs from history, but never invoke narrative directly.

7. Integration Points
   7.1 Runtime Tick & History

Per SOT-SIM4-RUNTIME-TICK:

Phase H: Diff Recording + History:

build_world_snapshot(...) is called for the current tick.

Snapshot is stored in HistoryBuffer.

episode_builder may be invoked to extend the current episode.

Phase I: Narrative Trigger:

NarrativeRuntimeContext builds NarrativeTickContext from:

latest WorldSnapshot,

AgentSnapshots derived from that snapshot,

recent events/diff.

7.2 Narrative Interface

Per SOT-SIM4-NARRATIVE-INTERFACE and SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT:

WorldSnapshot and AgentSnapshot are the primary context for:

NarrativeTickContext,

NarrativeEpisodeContext,

NarrativeUICallContext.

StageEpisodeV2 is passed into NarrativeEpisodeContext when narrative summarizes an episode.

Narrative may:

read snapshots and episodes,

never mutate them.

8. Extension Rules

You may extend the snapshot/episode layer by:

Adding new fields to snapshots/episodes:

only via SOT revision and with clear Rust mapping.

Adding new specialized snapshot types:

e.g. CrowdSnapshot, FactionSnapshot, ConflictSnapshot.

You must not:

smuggle engine handles or LLM objects into snapshot types.

let snapshot/ call into narrative or runtime code.

introduce nondeterminism in builders.

9. Completion Conditions for SOT-SIM4-SNAPSHOT-AND-EPISODE

This SOT is considered implemented and enforced when:

snapshot/world_snapshot.py defines:

WorldSnapshot, RoomSnapshot, AgentSnapshot, ItemSnapshot, and nested helper types as per §4.

snapshot/episode_types.py defines:

EpisodeMeta, EpisodeMood, DayWithScenes, SceneSnapshot, TensionSample, StageEpisodeV2, and EpisodeNarrativeFragment as per §5.

snapshot/world_snapshot_builder.py:

builds WorldSnapshot deterministically from WorldContext + ECSWorld,

does not mutate ECS/world,

does not call narrative or runtime.

snapshot/episode_builder.py:

maintains StageEpisodeV2 across ticks,

uses only history/snapshots/narrative outputs as inputs,

performs no simulation or narrative calls itself.

Runtime tick loop:

uses build_world_snapshot(...) and episode_builder in Phase H,

uses snapshots in NarrativeRuntimeContext Phase I.

No module in:

ecs/, world/, narrative/, or integration/
imports snapshot builders in a way that would create a circular dependency or leak layering.

At that point, the snapshot + episode layer is:

Sim4-correct,

stable as a cross-language schema,

a clean spine for:

narrative context,

history/replay,

frontend visualization,
without ever disturbing the deterministic core.