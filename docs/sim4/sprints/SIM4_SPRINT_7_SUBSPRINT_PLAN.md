✅ Sprint 7 — Snapshot & Episode

Sub-Sprint Plan (Junie-Friendly)

We break Sprint 7 into 7.0 → 7.6, each with:

Tight file scope

Clear exit criteria

No architectural drift

Minimal cross-directory scanning

🔹 7.0 — Snapshot SOT Deep Read (Read-Only Alignment)

Goal:
Give Junie a precise mental model of Snapshot & Episode before writing any code.

Files (Read-only)

Docs

docs/sim4/SOTs/SOT-SIM4-SNAPSHOT-AND-EPISODE.md

docs/sim4/SOTs/SOT-SIM4-RUNTIME-TICK.md

docs/sim4/SOTs/SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT.md

Code (read-only)

backend/sim4/runtime/tick.py

backend/sim4/runtime/events.py

backend/sim4/runtime/__init__.py

Tasks

Identify:

What the snapshot builder consumes

Where snapshot is called (Phase H)

Required episode entrypoints

List any missing runtime hooks relevant to Sprint 7 (but don’t implement).

Exit Criteria

A short inspection summary:

Where snapshot code will live

What runtime expects back

What episode builder must expose

🔹 7.1 — Snapshot DTO Schema (Types Only)

Goal:
Create all snapshot dataclasses — no builders, no logic.

Files

backend/sim4/snapshot/world_snapshot.py

Scope

Implement:

WorldSnapshot

RoomSnapshot

AgentSnapshot

ItemSnapshot

All nested helpers:

AgentSocialSnapshot

MotiveSnapshot

PlanSnapshot, PlanStepSnapshot

TransformSnapshot

Rules:

Dataclasses only

No ECS/world imports except identity enums or types

No logic

Rust-portable shapes

Exit Criteria

Imports clean

Dataclasses instantiate correctly

No logic inside DTOs

🔹 7.2 — Episode DTO Schema

Goal:
Lock the UI-facing episode types.

Files

backend/sim4/snapshot/episode_types.py

Scope

Implement:

EpisodeMeta

EpisodeMood

SceneSnapshot

TensionSample

DayWithScenes

StageEpisodeV2

EpisodeNarrativeFragment

Rules:

No builders

Pure dataclasses

Rust-portable

No narrative imports

Exit Criteria

DTOs import cleanly

Type hints align with SOT

No runtime coupling

🔹 7.3 — WorldSnapshot Builder (Minimal Complete Snapshot)

Goal:
Build deterministic WorldSnapshot from ECSWorld + WorldContext.

Files

backend/sim4/snapshot/world_snapshot_builder.py

backend/sim4/tests/snapshot/test_world_snapshot.py

Scope

Implement:

build_world_snapshot(
tick_index: int,
episode_id: int,
world_ctx: WorldContext,
ecs_world: ECSWorld,
) -> WorldSnapshot


Include:

Rooms from WorldContext

Agents from ECSWorld

Components:

Transform

RoomPresence

ActionState (if present)

NarrativeState (if present)

Deterministic sorting:

Rooms by ID

Agents by ID

Build lookup maps (room_index, agent_index)

Out of Scope

Social graph

Motives

Plan tree

Snapshot diff

Tests

One agent

One room

Deterministic output

Structural assertions only

Exit Criteria

✅ A snapshot can be built and passes tests.

🔹 7.4 — Episode Builder (Skeleton + First Functionality)

Goal:
Produce a valid but minimal StageEpisodeV2 from snapshots.

Files

backend/sim4/snapshot/episode_builder.py

backend/sim4/tests/snapshot/test_episode_builder.py

Scope

Implement:

start_new_episode()
append_tick_to_episode()
finalize_episode()


Initial behavior:

EpisodeMeta fields filled

1 Day

1 Scene

key_world_snapshots gets appended per tick

No mood computation yet

Out of Scope

Narrative integration

Scene segmentation logic

Tension metrics

Tests

Build an episode across 2 ticks

Validate:

tick ranges

snapshots inserted

meta fields updated

Exit Criteria

✅ A basic episode forms and mutates across ticks.

🔹 7.5 — Minimal Snapshot Diff (Optional but Strongly Recommended)

Goal:
Introduce forward-compatible diff structure.

Files

backend/sim4/snapshot/diff_types.py

backend/sim4/snapshot/snapshot_diff.py (if used)

Scope

Implement:

SnapshotDiff

EntityDiff

RoomDiff

Initial diff rules:

Compare by ID + field value

Only detect:

Room change

Missing entity

Position change

No history storage yet.

Exit Criteria

✅ Snapshot diff is computable between two WorldSnapshots.

🔹 7.6 — Sprint 7 Closure & API Polish

Goal:
Lock surface area for Sprint 8 (narrative consumption).

Files

backend/sim4/snapshot/__init__.py

SOT update (status section)

Implementation report section

Tasks

Expose:

from sim4.snapshot import (
build_world_snapshot,
start_new_episode,
append_tick_to_episode,
finalize_episode,
WorldSnapshot,
StageEpisodeV2,
)


Add:

“✅ Implemented in Sprint 7” status to SOT

Document:

What’s missing

How narrative will consume snapshots

Performance assumptions

Exit Criteria

✅ Runtime can import snapshot cleanly
✅ Narrative contract is unambiguous

🔮 Sprint 8 Preview (Very Brief)

Sprint 8 will then attach:

Area	Purpose
Narrative DTOs	NarrativeTickContext
NarrativeRuntimeContext	Phase I bridge
ExternalCommandSink	Delayed ECS injection
Budget contracts	Control invocation

But Sprint 7 ends with:

✅ Snapshots become the sole narrative input form