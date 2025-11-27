🌅 Era III Backend Master Vision (Finalized)
StageEpisodeV2-aligned, architecturally clean, simulation-first, identity-driven.

Era III is a ground-up redesign of Loopforge’s simulation backend to support:

Structured worlds with spatial layouts

Explicit identity-layer for agents

Scenario-driven config

Rich time model (ticks → beats → scenes → days)

Structured recorder

EpisodeBuilder that produces StageEpisodeV2 directly

A backend that is modular, testable, and expandable

A frontend contract that is stable and expressive for UX

This version is the North Star for every file we write going forward.

🌄 1. Simulation Principles

Era III backend follows five core design principles:

1. Story-first, architecture-second

Every backend component exists to enable:

readable days

meaningful scenes

richer cast identity

spatial tension

clear tension trends

narrative surface area

2. Layer discipline

Modules are separated by responsibility:

Layer	Responsibility
Identity	Agents, types, roles, stress signatures
World	Structured spatial environment
Scenario	Combination of world + cast + parameters
Time	Tick → Beat → Scene → Day
Sim Engine	Agent logic, tension propagation, events
Recorder	Structured logging
EpisodeBuilder	Transform logs to StageEpisodeV2
3. No ad-hoc global values

Everything is resolved via:

identity registries

world identity registry

scenario builder/loader

4. UI contract drives backend structure

The backend emits StageEpisodeV2 directly.
No ad-hoc transformations inside the frontend.

5. Deterministic + testable

All outputs (world snapshot, cast metadata, days, scenes, mood) must be:

deterministic given a random seed

reproducible

assertable in tests

💠 2. Identity Layer (Agents, Roles, Types)

(This is the core innovation in Era III — the cast is no longer a list of names.)

The identity system defines:

AgentType – base mechanical/psychological type

RoleIdentity – functional/narrative role

AgentInstance – scenario-level instantiation

CastPreset – group presets for scenarios

2.1 AgentType

Defines defaults:

type name

base vibe

archetype

color theme

icon

stress baseline + volatility

default narrative hooks

2.2 RoleIdentity

Defines:

“Maintenance Bot”, “Supervisor”, “Line Worker”

stress multipliers

room affinity

narrative role tags

2.3 AgentInstance

Scenario-level instantiation:

AgentInstance {
id: "sprocket",
type: "worker_bot",
role: "maintenance",
presets: { stressProfile overrides, color override, name override }
}

2.4 CastPreset

Named presets for scenarios:

"default_four_bots"

"maintenance_heavy"

"supervisor_shift"

Output:
These identities merge into AgentCharacterSheet (UI-facing).

🏭 3. World Identity Layer

(Worlds are no longer list of room strings — they are structured spatial entities.)

3.1 WorldIdentity

Contains:

id & name

set of rooms

adjacency

base world traits (noise, instability, etc.)

size ("small", "medium", "large")

description

3.2 RoomIdentity

Defines:

id

label

kind (“floor”, “control”, “storage”)

no position yet (added later)

adjacency (redundant allowed; validated)

base tension

hazards

visual tags

3.3 BoardLayoutSpec

Optional:

default coordinates

UI hints

canonical layout mapping

3.4 WorldSnapshot

The UI-facing version includes:

rooms with positions

computed size

adjacency

base tension

visual tags

WorldSnapshot is produced by WorldSnapshotBuilder, not by identity code.

🕰️ 4. Time Model (Ticks → Beats → Scenes → Days)

(This enables storyboard mode, scene cards, tension strip, and day summaries.)

4.1 Tick

Lowest atomic step:

agent perception

planning

updates

events emitted

4.2 Beat

Grouping of ticks.
A beat is created when:

time threshold hit

or meaningful event occurs

4.3 SceneUnit

A “moment that matters”.
Produced when a beat satisfies "scene trigger":

tension changes

incident occurs

room changed

important agent acts

supervisor activity

any narrative tag event

SceneUnit fields (already in runtime_types):

id

dayIndex

index

timeCode

mainRoomId

involvedAgents

tensionTier

tensionDelta

summary

narrativeTags

4.4 DaySummary

A rollup:

tension curve

incidents

supervisor activity

primary room

dominant agents

1-sentence summary

4.5 DayWithScenes

Extends DaySummary with ordered scenes.

🎛️ 5. Scenario System

A scenario defines:

which world to load

how many days/ticks

which cast preset to use

stress volatility

fault rate

narrative settings

ScenarioIdentity
ScenarioIdentity {
id,
name,
worldId,
castPresetId,
parameters: {
ticksPerDay,
days,
volatility,
instabilityFactor,
faultRate
}
}


ScenarioConfig in Sim3 is a low-level resolver of:

worldId

custom_cast (optional)

parameters

ScenarioIdentity (future) is registry-level.

🎮 6. Sim Engine Layer

Responsible for:

tick loop

beat grouping

tension propagation

room updates

agent stress adjustments

event generation

supervisor triggers

Responsibilities:

IdentityResolver
merges types, roles, presets into AgentInstance → CharacterSheets

WorldBuilder
loads world identity → runtime world state

SimController
tick steps

EventEmitter
constructs structured tick events

BeatMaker
groups ticks → beats

SceneTriggerEngine
turns beats into scenes

DayBoundaryEngine
groups ticks into days

📘 7. Recorder Layer

The recorder stores:

tick events

beat metadata

scene triggers

per-day bundles

tension timeline

Everything is structured, typed, and chronological.

Output must be deterministic and testable.

🧱 8. EpisodeBuilder Layer

Transforms recorder logs into StageEpisodeV2.

StageEpisodeV2 includes:

version

episode meta

world snapshot

cast (character sheets)

days (with summaries + scenes)

tension trend

episode mood

The EpisodeBuilder is the only place where logs turn into UI objects.

🦋 9. Frontend Ground Truth: StageEpisodeV2

This is the anchor for everything.
Every type, scenario, world, identity, and log exists to populate:

{
version,
episode,
world,
cast,
days[],
episodeMood,
tensionTrend[]
}


This is the non-negotiable output format.

🧩 10. Era III Module Map

The Sim3 backend will contain the following top-level modules:

loopforge_sim3/
identity/
agent_types.py
roles.py
character_registry.py

world/
world_registry.py
world_identity.py
world_snapshot_builder.py

config/
scenario_config.py
scenario_registry.py

types/
identity_types.py
world_types.py
event_types.py
runtime_types.py

state/
sim_state.py
world_state.py
agent_state.py

sim/
controller.py
event_emitter.py
beat_engine.py
scene_trigger.py
day_engine.py

recorder/
trace_recorder.py

episode/
episode_builder.py

utils/
rng.py


This is the final structure we target.