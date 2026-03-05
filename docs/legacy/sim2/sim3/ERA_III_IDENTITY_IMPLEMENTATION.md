# 🌆 Sim3 – Era III Identity Layer
Backend Implementation Document (for new architects & maintainers)

Version: 2025-11 (Era III)

0. Purpose of This Document

This document explains:

What the Era III Identity Layer is

How it fits the long-term StageEpisode / Loopforge Vision

How the world, agents, events, and traces relate

What the frontend requires and why

Quickstart onboarding guide for new backend architects

How to maintain + expand identity safely

Which downstream systems rely on which identity types

This document is forward-compatible with Era IV (playback) and Era V (multi-world simulation) without drifting from our commitments.

1. Era III Identity Layer — What It Is

Era III Identity is the static, canonical definition of:

✔ Agents

What they are

What they look like

What stresses them

What role they play

How they should appear in UI character sheets

✔ World

Rooms, their hazards and tension baselines

Room kinds (floor, control, storage)

Adjacency graph

Optional layout templates

✔ Events & Narrative Time

Atomic tick events

Beat metadata

Scene units

Day summaries

Episode mood

✔ Traces

The minimal intermediate structures used to record simulation output and build StageEpisodeV2.

Identity is static. Runtime modifies state. Snapshot production transforms runtime + identity → UI payloads.

2. Why Identity Exists — Vision Alignment

This section ties identity to the StageEpisode Vision.

Vision Goals (condensed)

World you can see

Rooms positioned with meaning

Tension changes visible

Spatial context

Cast you can follow

Recognizable personalities

Color themes, archetypes, vibe

Days feel like scenes, not logs

Scene cards

Day storyboards

Episode banner moods

Actors move through world, not baked into cards

Agents change rooms, roles, stress, flags

Movement is visualizable

Identity supports this by creating three clean layers:

2.1 Identity → Runtime → Snapshot
1. Identity (Static)

Defines the world, rooms, agent types, roles, cast presets, and deep DNA of the scenario.

2. Runtime (Mutable)

Simulation step-by-step state:

world tension

room incidents

where agents stand

stress

dynamic flags

3. Snapshot (UI-facing)

Fully derived:

room coordinates

tension tiers

cast sheets

scenes & days

world map as the user sees it

Identity matters because everything stems from it.
Simulation only “moves” identity around. UI only “renders” identity + runtime together.

We never want the frontend to guess or infer identity. Everything must come from these types.

3. Modules Included in Era III Identity
   ✔ identity_types.py

AgentTypeDefinition, RoleIdentity, CastPreset, AgentIdentity, CharacterSheet

✔ world_types.py

WorldIdentity, RoomIdentity, BoardLayoutSpec + Runtime + Snapshot layers

✔ runtime_types.py

AgentState + SimState
(WorldState lives in world_types)

✔ event_types.py

TickEvent → BeatMetadata → SceneUnit → DaySummary → DayWithScenes → EpisodeMood

✔ trace_types.py

TickTrace → PresenceTrace → BeatTrace → SceneTrace → DayTrace

✔ episode_types.py

StageEpisodeV2 with optional traceAnchors

4. How Identity Fits Frontend Requirements

The frontend requires:

✔ Static world and cast definitions

Frontend must receive complete identity every time (colorTheme, archetype, vibe, etc.)

✔ Snapshot, not runtime

Frontend receives snapshots, not internal logic or state transitions.

✔ Spatial world

WorldSnapshot contains room positions, sizes, adjacency.

✔ Tension tiers

RoomSnapshot reports tier (“low”, “medium”, “high”, “critical”), not raw floats.

✔ Narrative structure

Frontend needs:

days

scenes

banners

tension trend

cast

✔ Future scrubbing support

A small optional future hook:

traceAnchors: {"firstSceneTick": 12, "climaxTick": 240}


Identity defines the shape of these objects.
Backend (EpisodeBuilder) fills them in.

5. Quickstart Guide for New Backend Architects
   “I just joined the Loopforge team — how do I work with Sim3 identity?”
   Step 1: Understand the 3-layer model
   Identity (static DNA)
   Runtime (mutable state)
   Snapshot (UI)


Identity originates in:

scenario config

agent type registry

world registry

Runtime evolves on each tick.
Snapshot is built at the end of each tick/day/episode.

Step 2: Know the canonical entrypoints
To build the world:
WorldIdentity  →  WorldState  →  WorldSnapshot

To build agents:
AgentTypeDefinition + RoleIdentity + InstanceConfig
→ AgentIdentity
→ AgentState
→ AgentCharacterSheet

To build time narrative:
TickEvent → BeatMetadata → SceneUnit → DaySummary → EpisodeMood

To build trace:
TickTrace → BeatTrace → SceneTrace → DayTrace

To build the final UI:
EpisodeBuilder → StageEpisodeV2

Step 3: You only mutate runtime, never identity

Identity objects are all @dataclass(frozen=True).
Do not use identity for mutable flags.

Step 4: Where to add new features?
Want a new world attribute?

Add to WorldIdentity

Want new agent stress mechanics?

Add to AgentState or StressProfile

Want new scene extraction logic?

Modify BeatEngine → SceneTrigger

Want new UI data?

Add to:

RoomSnapshot

WorldSnapshot

AgentCharacterSheet

or StageEpisodeV2

But never add runtime data directly to snapshots.

6. Maintenance Guidelines
1. Identity modules must stay pure

No side effects
No runtime references
No circular imports
FROZEN dataclasses only

2. Runtime modules never import UI types

SimState should not know what a RoomSnapshot is.

3. Snapshot modules never modify runtime

Snapshot builders compute a new object every time.

4. Trace types should remain minimal

Everything in trace types must be:

representable from TickEvent

not exceeding memory constraints

backend-only

5. Episode types are UI contract

Changing them = breaking API.

Lock them unless frontend architect approves.

7. Who Uses What?
   Mapping identity to future Era III systems
   System	Identity Types Used	Why
   WorldBuilder / ScenarioLoader	WorldIdentity, RoomIdentity	Constructs world runtime state
   Sim Initialization	AgentIdentity, WorldIdentity	Seeds AgentState + WorldState
   Tick Engine	WorldState, AgentState, Event Types	Computes deltas per tick
   EventEmitter	TickEvent	Emits tick-level narrative signals
   BeatEngine	BeatMetadata	Compresses ticks into beats
   SceneTrigger	SceneUnit	Builds narrative scene moments
   DayEngine	DaySummary, DayWithScenes	Aggregates scenes into days
   TraceRecorder	TickTrace, BeatTrace, SceneTrace, DayTrace	Stores intermediate trace
   Snapshot Builders	WorldSnapshot, RoomSnapshot	Build UI-ready frames
   EpisodeBuilder	StageEpisodeV2	Final payload for UI

This table ensures no one misuses identity or runtime layers.

8. Summary — Identity in Era III

Identity Layer is the ground truth for:

world structure

cast definitions

narrative time model

event classification

trace scaffolding

episode structure

It is static, immutable, UI-influenced, and runtime-agnostic.

Era III simulation is built on the principle:

Identity defines the world. Runtime fills it with life. Snapshots tell the story.