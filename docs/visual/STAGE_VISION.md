✅ 0. Reality Check — Current State Summary (True System Snapshot)

(“The anchor point” — this keeps future grand visions tethered to what’s actually built.)

🔹 Backend

The backend is stable.
Specifically:

Identity is correct across logs → analytics → registry → StageEpisode.

Trait system is canonicalized (5 traits only).

StageEpisode builder works and is defensive.

EpisodeSummary + DaySummary are consistent, additive, versioned.

API endpoints work reliably:

/episodes

/episodes/latest

/episodes/{id}

/episodes/{id}/raw

Everything needed for Phase 1 UI is already exposed and stable.

🔹 API Layer

Proper FastAPI app with CORS configured for Vite.

Endpoints return full StageEpisode JSON including:

emotion_states

belief_attributions

reflection_states

world_pulse

long_memory

story_arc

supervisor weather

attribution drift

character visuals/vibes/taglines

structured day-level narratives

None of the complexity is yet used by the frontend.

🔹 Frontend (ui-stage)

Right now:

Folder Structure
ui-stage/
src/
types/stage.ts     ← incomplete StageEpisode types
App.tsx            ← fetch latest episode + dump lists
assets/
index.css
App.css
main.tsx

Behavior

Fetches /episodes/latest

Displays:

episode metadata

agent start/end stress

tension trend list

No layout

No components

No timeline

No visual encodings

No interactivity

No use of cognitive layers
(beliefs, attributions, emotions, narrative, arcs, long-memory… all unused)

Types

Types do NOT match the backend contract.
Missing:

narrative

traits

story arc

long-memory

agent role

emotional structures (typed as string instead of object)

agent/narrative-specific fields

Testing

Only a smoke test: expect(true).toBe(true)

Conclusion:
The UI is connected but not structured.
No view-model contract. No components. No visual language yet.

🟦 1. Marquee’s Start-of-Cycle Vision (Rewritten, Realistic, and Grounded in Actual Code)

This is the official “Architect Charter” for the visual system lineage.

🎭 Marquee: Vision for the Stage

(Puppetteer → Gantry → Stagemaker → Marquee)

Loopforge’s simulation has matured.
The backend now produces something remarkable:

structured cognition.
Beliefs.
Attributions.
Emotional arcs.
Reflections.
World pulse.
Long memory.
Story arcs.
Supervisor weather.

Front-end currently displays none of this.

Marquee’s job is to change that.

🎯 Objective of the Visual System

Make the inner life of the agents
visible, readable, and dramatically expressive,
using a stable contract with the backend.

The Stage must serve three masters:

1. The Founder

A tool to see what the simulation is thinking and debug the model.

2. The Audience

A readable story that reveals tension, emotion, conflict, progression.

3. Future Architects

A clean visual contract so rendering layers (2D/3D/cinematic/live-mode) can evolve without breaking.

🟩 2. Long-Term Visual Roadmap (Rewritten for Current Reality)

Divided into eras, not just phases.

ERA I — Foundation of the Viewer (now → next few sprints)

Goal: Build a UI skeleton that can read everything from StageEpisode safely.

Deliverables:
1. Exact Type Synchronization

Bring stage.ts into full parity with backend:

StageNarrativeBlock

StageAgentTraits

emotion_states

attribution objects

story_arc

long_memory

character visuals/vibes/taglines

day-level narrative

roles

trait snapshots

Why it matters:
Everything downstream depends on the type layer being real.

2. View Model Layer (VM Layer)

Create derived UI-safe structures:

vm/episode.vm.ts
vm/agent.vm.ts
vm/day.vm.ts


Purpose:

Normalize nulls

Provide defaults

Flatten nested objects

Pre-compute percentages, slopes, deltas

This decouples UI from StageEpisode version bumps.

3. Episode Player Shell

Decompose App:

App → EpisodeLoader → EpisodePlayer
↳ EpisodeHeader
↳ Timeline
↳ DayViewer
↳ AgentList

4. Basic Visual Language

Minimal but expressive:

Background tension gradient (day-level)

Simple timeline scrubber

Agent bar with stress progression

Agent avatar seeded by “visual/vibe/tagline”

Incidents highlighted

At this stage:
No animations, no interactions beyond scrubbing days.

ERA II — Cognitive Readability Layer

This is Loopforge’s actual prize.

Goal:
Turn abstract cognition into cinematic clarity.

Deliverables:
1. Belief Maps

Per agent:

what they believed today

who they blamed

certainty arcs

attribution drift

Rendered as:

color-coded chips

micro-diagrams

side-panel cognitive sheet

2. Emotional Weather

Animated tone ring / aura around each agent:

stress

mood

agitation

calm

supervisor-induced modulation

3. Reflection / Narrative Integration

Render each agent’s reflection block:

concise quotes

emotional takeaways

unresolved tensions

Day-level narrative appears as:

beat cards

infoboxes

timeline footnotes

4. Story Arc Visual

Episode-level:

rising action

peak tension

resolution/not-resolved indicator

This creates the rhythm of a “robot drama.”

ERA III — Live Mode

Now that the UI can render cognition cleanly, enable incremental simulation.

Needs backend support:

POST /run or POST /episodes/run

Day-by-day output

Step-by-step deltas

Stream or poll

UI:

Producer Console

Start/Stop/Step

Live Stage Renderer

Tension meter animating in real time

Agent nodes pulsing with state changes

Supervisor weather tracking as gradient shifts

This is where Loopforge becomes watchable.

ERA IV — Renderer Abstraction

Goal: allow multiple rendering backends to plug into the same StageEpisode VM:

Renderer2D

Renderer3D

RendererTheatre (cinematic)

RendererDebug (pure charts/debug panels)

The UI becomes a router of views; StageEpisode stays constant.

ERA V — Ecosystem Features

Optional but unlocked by a stable Viewer:

Episode Library

Tagging + search filters

Compare episodes side-by-side

Export as video/storyboard

“Director Notes” annotation layer

🟧 3. Critical Sync Rules (Backend ↔ Visual System)

To keep the visual lineage stable:

Rule 1 — Backend adds; never mutates previously exposed fields.

Frontend types rely on additive growth.

Rule 2 — StageEpisode has versioning; VM layer handles migration.
Rule 3 — Narrative, emotion, attribution, traits, long-memory

must be treated as pure read-only maps for UI.

Rule 4 — UI always uses view-model, never raw API models.
Rule 5 — Visual encodings must align with psychological meaning.

No misleading color/shape choices.

- Marquee