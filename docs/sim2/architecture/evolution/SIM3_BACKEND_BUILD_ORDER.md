# ✅ Sim3 Backend Build Order (Authoritative Sequence)

_(focus: minimal modules needed to produce `StageEpisodeV2`)_

## PHASE 1 — Foundations (CURRENT)

These are already done:
### 1. `world/world_registry.py`
Source of truth for world layouts.
### 2. `config/scenario_config.py`
Scenario parameters (world selection, cast selection, temporal config).

✔ Done.

---

## PHASE 2 — Core Simulation Primitives
Before we can build episodes, we must define the minimal runtime structures:
### 3. `types/runtime_types.py`
**Purpose:** canonical small types used across the sim.

This includes:
* `WorldSnapshot` (the UI-ready world layer, stripped down from registry)
* `RoomSnapshot`
* `AgentRuntimeState` (position, stress, status — minimal, no behavior yet)
* `DaySummary`, `SceneUnit`, `EpisodeMood` (data classes matching frontend spec)
* Utility enums: `TensionTier`

These are **data-only**, no logic — critical to avoid circular imports.

> This file is the backbone of the whole stack.

---

### 4. `state/sim_state.py`
Minimum viable simulation state container.

Not full sim.  
Not full agent physics.  
Just:
* current tick
* current day
* positions of agents
* world layout ref
* tension accumulation buffer
* event log buffer

Why? Because **EpisodeBuilder needs state snapshots**.

---

### 5. `runner/sim_runner.py`

Tiny orchestration class.

For now:

run_scenario(config: ScenarioConfig) -> EpisodeRawLogs

Later:

tick loop

default agent behavior (random or stub)

tension scoring (stub)

event capture

This is NOT the old Loopforge runner.
This is a Sim3 mini-runner purely for producing raw traces → StageEpisode.

PHASE 3 — Episode Construction Layer

Once raw logs exist, we can build real Episode structures.

6. episodes/episode_meta.py

Matches the frontend spec exactly.

Contains:

EpisodeMeta

RunMeta

ID generation helpers

No logic.

7. episodes/world_snapshot_builder.py

Transforms backend WORLD_LAYOUTS into the frontend’s WorldSnapshot schema.

This file handles:

mapping registry zones → rooms

adding canonical coordinates (grid positions)

adding room kinds + default visual tags

mapping adjacency cleanly

This is extremely small.

8. episodes/cast_builder.py

Transforms CHARACTERS → UI-ready AgentCharacterSheet.

Also sets:

colorTheme

iconKey

archetype

narrativeHooks

Rules can be simple — even random defaults — until agent semantics mature.

9. episodes/day_scene_builder.py

Processes raw logs to extract:

daily tension scores

per-day summaries

primary room

dominant agents

count of incidents

per-scene entries

This is the biggest logic file but still algorithmically simple.

10. episodes/episode_mood_builder.py

Computes:

episode-wide tension arc

mood tier: calm / rising / volatile / decompression

mood summary string

Stub is acceptable initially.

11. episodes/episode_builder.py

🎯 Final assembly into:

StageEpisodeV2

Combines:

EpisodeMeta

WorldSnapshot

Cast sheets

Day summaries

Scenes

EpisodeMood

TensionTrend

This file is the top of the pyramid.

PHASE 4 — Integration / API Layer
12. api/episode_api.py

Optional but recommended.

Provides:

generate_episode(config: ScenarioConfig) -> StageEpisodeV2

Thin wrapper around runner → builder

This is what your UI (or CLI) calls.

Summary of the Correct Order

Here is the exact sequence:

PHASE 1 (Done)
1. world/world_registry.py
2. config/scenario_config.py

PHASE 2 (Core Runtime)
3. types/runtime_types.py
4. state/sim_state.py
5. runner/sim_runner.py

PHASE 3 (Episode Builders)
6. episodes/episode_meta.py
7. episodes/world_snapshot_builder.py
8. episodes/cast_builder.py
9. episodes/day_scene_builder.py
10. episodes/episode_mood_builder.py
11. episodes/episode_builder.py

PHASE 4 (API)
12. api/episode_api.py