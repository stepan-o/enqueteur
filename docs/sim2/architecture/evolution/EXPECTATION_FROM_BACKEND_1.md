Frontend Expectations for Loopforge Stage

(What the UI needs from the backend to become a real “stage”, not just a debugger)

0. Why this exists

Right now, the UI can read episodes, days, agents, tension scores, and narrative text. That’s enough to build a pretty debugger.

The next generation frontend is explicitly aiming for:

Stage – a visible world (rooms, layout, heat).

Cast – agents that occupy that world in a readable way.

Story – episodes that play out as scenes, not just lists.

This document describes what the frontend expects from the backend so that we can build that stage in a principled way, instead of guessing from aggregates.

This is not dictating implementation details. It’s a contract:
“If the backend can give us at least this, we can reliably build the stage-like interface you actually want.”

1. High-level principles

Additive, not breaking

Existing consumers of StageEpisode / EpisodeViewModel must continue to work.

New structures are added alongside current ones, with clear versioning.

Stage-first vocabulary

Backend objects should speak in terms of rooms, events, agents, days, not only “scores” and “totals”.

The world should be canonical – frontend should not invent core spatial facts.

Coarse but structured

We do not need high-frequency logs or full trajectories.

We do need a small, structured summary that is faithful to the simulation.

Graceful absence

All new fields can be optional.

If data is missing, the UI will fall back to the current “single-room” world.

2. Priority tiers

To make this concrete, frontend expectations are split into tiers.

Tier 1 — Required for Stage Map 2.0 & Story Mode 1.0

(needed for the next frontend architect to move meaningfully forward)

A Stage World descriptor per stage_version.

Per-day room snapshots inside the episode.

Tier 2 — Strongly desired soon after

(unlocks micro-motion, better overlays)

A coarse list of events (beats) with location + actors.

Optional belief vs true cause metadata for some events.

Tier 3 — Future-friendly, nice-to-have

A small agent manifest for visuals (portraits, vibe hints).

The rest of this doc specifies those tiers in more detail.

3. Tier 1 – Stage World & Room Snapshots
   3.1 Stage World descriptor

Expectation

For each stage_version, the frontend can retrieve a canonical description of the world:

interface StageWorldRoom {
id: string;          // "control_room"
label: string;       // "Control Room"
kind?: string;       // "control" | "flow" | "buffer" | ...
layout_hint?: {      // coarse grid positions, *not* pixels
x: number;
y: number;
};
}

interface StageWorldEdge {
from: string;        // room_id
to: string;          // room_id
}

interface StageWorld {
stage_version: number;
rooms: StageWorldRoom[];
edges?: StageWorldEdge[];
}


How frontend will use this

Build the Stage Map board: each room becomes a tile/node.

Use layout_hint and edges to place rooms and draw simple connections.

Use kind to vary icons/appearance later (“control vs storage vs flow”).

Minimum viable version

3–10 rooms per stage.

Optional or simple layout_hint (even a 2×2 grid is enough).

Edges can be omitted initially; frontend can still layout rooms in a grid.

Where it lives

Either embedded in the episode payload (e.g. _world), or available via a small getStageWorld(stage_version) endpoint.

Frontend only cares that given a stage_version, it can get a StageWorld.

3.2 Per-day room snapshots

Expectation

Extend StageEpisode with optional per-day room snapshots. Schema sketch:

interface StageRoomSnapshot {
room_id: string;        // must match StageWorld.rooms.id
tension_score: number;  // 0..1, same scale as existing tension_scores
incident_count: number;
active_agents: string[]; // agent names as used in episode.agents keys
}

interface StageDaySnapshot {
day_index: number;        // aligns with existing days[].day_index
rooms: StageRoomSnapshot[];
}

interface StageEpisode {
// existing fields...

stage_snapshots?: StageDaySnapshot[];
}


Semantics & invariants

stage_snapshots may be missing entirely → frontend falls back to “Factory Floor only”.

If present:

Every day_index used in stage_snapshots refers to an existing day.

rooms[].room_id values are a subset of StageWorld.rooms.id.

Scores are coarse summaries of that day in that room, not precise integrals.

How frontend will use this

Stage Map 2.0 becomes a view over StageWorld + stage_snapshots:

For selected day: show all rooms with room-specific tension, incidents, and active agent initials.

For Story Mode: highlight the primary room(s) per day/scene.

Story Mode cards will say things like:

“Day 1 — Conveyor was hot (high tension, 2 incidents) with Nova & Sprocket.”

Minimum viable version

Even a single room snapshot per day is useful.

If only one room is meaningfully simulated per day, you can still use multiple room IDs but give them 0 tension and 0 incidents as appropriate.

active_agents can be approximate (e.g., top 2–3 by activity).

4. Tier 2 – Events & Belief Metadata

These are not required for the immediate next cycle, but frontend will start using them as soon as they appear.

4.1 Events (beats) – coarse intra-day structure

Expectation

Optional list of events attached to the episode:

interface StageEvent {
id?: string;              // optional stable id
day_index: number;
step: number;             // coarse ordering within the day
room_id: string;          // must match StageWorld.rooms.id
actors: string[];         // agent names
targets?: string[];       // agent names or "system"/"environment"
event_type: string;       // "check_failed" | "repair" | "warn" | etc.
severity?: number;        // 0..1
narrative_snippet?: string;
true_cause?: string;      // see below
agent_beliefs?: { [agentName: string]: string }; // agent → perceived cause
}

interface StageEpisode {
// existing fields...

events?: StageEvent[];
}


Semantics

events may be absent or an empty array.

step is only required to be increasing within (day_index).

event_type is a free-form string but should be stable enough for simple mapping.

room_id should match StageWorld.

How frontend will use this

Drive micro-motion:

pulse rooms when events fire;

shake agent portraits on high-severity events;

timeline markers in StageView.

Drive Story Mode details:

“On Day 1 in Conveyor, check_failed event with Nova (severity 0.8).”

Eventually: allow “event list” debugging on the Details side.

4.2 Belief vs true cause metadata

Expectation

For some events (not necessarily all), backend may fill:

true_cause: "system" | "random" | "human" | "environment" | ...

agent_beliefs[agentName]: same vocabulary but from the agent’s POV.

How frontend will use this

Lightweight overlays:

small icons / misalignment bars where belief ≠ true cause.

future “belief vs reality” panels filtered by event.

Minimum expectation

Not blocked for UI: events can exist with no belief metadata.

When belief info is present, we expect it to be internally consistent (e.g., values from a small finite set).

5. Tier 3 – Agent Manifest for Visuals

This tier directly supports stronger cast presence and portraits.

Expectation

A per-episode or per-stage agent manifest with stable visual hints.

Sketch:

interface AgentVisualManifest {
name: string;            // must match EpisodeViewModel.agent name
visual_id?: string;      // "delta" | "nova" | "sprocket"
vibe?: string;           // "focused" | "anxious" | "calm" | ...
base_color?: string;     // hex or token id
portraits?: {
neutral?: string;      // asset id or URL
stressed?: string;
calm?: string;
};
}


Frontend will:

Use visual_id / portrait references to render actual faces instead of generic blobs.

Map vibe/base_color to the existing vibeColorKey and stress auras.

Treat all of this as optional:

If absent, we still use the current procedural avatars.

This manifest can live in:

StageEpisode._raw.character_defs, or

a separate lookup keyed by stage version or run id.

6. Invariants & guarantees frontend will rely on

To avoid accidental footguns, these are the key invariants frontend will treat as guaranteed once we move to Stage 2.0:

Day indices

day_index is 0-based and contiguous within an episode.

StageEpisode.days[i].day_index and stage_snapshots[].day_index refer to the same conceptual day.

Room IDs

StageWorld.rooms[].id are stable across episodes for a given stage_version.

All room_id references in stage_snapshots and events are members of StageWorld.rooms.id.

Agent naming

Names used in:

StageEpisode._raw.days[].agents

StageEpisode._raw.agents

stage_snapshots[].rooms[].active_agents

events[].actors / events[].targets / events[].agent_beliefs
refer to the same conceptual agents (identical strings).

Scales

tension_score and severity are always in [0, 1] or documented if different.

Day-level tension_score is consistent with room-level scores (e.g., average or max, but not contradictory).

Optionality

New arrays (stage_snapshots, events) may be absent.

When absent, they should be completely omitted or set to [], not null with partial contents.

Frontend will treat missing arrays as “feature not available yet” and render the current simpler view.

7. How this will be used in practice

Once the backend provides Tier 1 (and ideally Tier 2 soon after), the next frontend architect can:

Upgrade StageView to:

render a proper board of rooms (from StageWorld.rooms).

shade rooms per selected day, per stage_snapshots.

show agent chips based on active_agents.

Build Story Mode v1:

one card per day, showing key agents + primary room label (from snapshots).

clicking a card syncs StageMap and the Details view.

Then, with events + belief metadata:

Add micro-motion tied to events.

Build belief vs truth overlays based on real divergence data instead of generic labels.

And with an agent manifest:

Replace “blobs with letters” by genuine portraits and richer cast identity.

All of that is achievable without exploding backend complexity, so long as the world, rooms, and events are first-class in the data model.

8. Summary (TL;DR for backend architect)

If you only read one section, read this:

Frontend needs:

A canonical StageWorld per stage_version (rooms [+ optional layout/edges]).

Optional per-day stage_snapshots that say: for each room on Day N, how “hot” it was and which agents were active.

Optionally, a coarse events[] list with day, room, actors, and event_type (+ optional cause/belief metadata).

Optionally, a small agent visual manifest (portraits/vibes/colors).

If we have those, we can:

Stop faking the world in the frontend.

Build StageView as a real board instead of a decorated list.

Turn episodes into scenes on a visible stage with a recognizable cast.

That’s the alignment point this doc is asking for.