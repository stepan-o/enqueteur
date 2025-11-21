🌆 LOOPFORGE STAGE ROADMAP — LONG-TERM VISION
0. Ground Rules for the Roadmap

Story first, infra second. Every phase must make episodes more interesting to watch or easier to understand.

Layer discipline.

Sim & mind: core, psych, analytics, narrative

Visual data bridge: stage

Access: api

Frontend: ui-stage

No throwaway phases. Each phase must be a stable foundation for the next, not a prototype to be discarded.

Phase 0 — Stage API Foundations

“Give the show a backbone.”

Purpose

Create the StageEpisode concept and a minimal service layer so everything visual has a clean, versioned data model to build on.

This is the “we’re still in back-of-house, but we’re thinking like theatre now” phase.

What it aims to accomplish

Canonize the Stage data contract

Introduce StageEpisode and supporting DTOs.

Define what the Stage gets:

days, tension trend, per-agent stats

story arc

long memory snapshots

narrative intros/outros + agent beats.

Wire it into existing logic

Use analytics + narrative + psych outputs to build StageEpisode.

Implement loopforge.stage.build_stage_episode(...).

Expose episodes via API

Add loopforge.api with endpoints like:

GET /episodes → list known episodes

GET /episodes/{id} → StageEpisode JSON

(Optional) GET /episodes/{id}/raw for full export

Layers touched

schema — define StageEpisode types (or referenced by stage)

analytics / narrative — minor adjustments to support Stage data needs

stage — new layer with builder functions

api — new layer serving StageEpisodes

cli — optionally add commands to run the API

Concrete deliverables

StageEpisode dataclass (+ docstring / MD spec)

loopforge.stage module with:

build_stage_episode(...)

loopforge.api FastAPI app with:

/episodes

/episodes/{id}

Simple file-based run registry or reuse existing registry

Estimate

1–2 Junie-sprints

Sprint 1: data model + builder + basic run registry

Sprint 2: API wiring + tests + simple docs

✅ Feels like: “Can be done in a cycle (or two),” not a multi-month project.

Phase 1 — Episode Player v1 (Static Stage)

“Let’s actually watch a robot episode.”

Purpose

Ship a first visible Stage: a small web app that can load a StageEpisode and show it in a simple, readable way.

No live streaming, no 3D yet. Just proof that Loopforge is a watchable drama.

What it aims to accomplish

Create the ui-stage app

React + TypeScript + Vite (or Next).

Minimal routing: single-page “Episode Player.”

Implement a 2D StageRenderer

Agents as circles/nodes.

Background color/gradient for tension.

Simple indicators for stress, guardrails vs context.

Replay episodes day-by-day

Load a StageEpisode from GET /episodes/{id}.

Day timeline strip (click to jump between days).

Text panel with:

Day intro/outro

Key agent beats.

Establish the component architecture

EpisodePlayer

StageRenderer2D

AgentAvatar

NarrativePanel

EpisodeTimeline

Layers touched

api — maybe tweaks to better support the UI (e.g., episode listing)

ui-stage — new frontend app with React components

Concrete deliverables

/ui-stage project created & running locally.

Basic UI that:

fetches /episodes

lets you select one

plays through days visually.

Minimal styling, but not hideous.

Estimate

2 Junie-sprints

Sprint 1: UI scaffold, API integration, basic static rendering.

Sprint 2: UX polish, timeline, narrative panel, refactors.

🟨 Feels like: “You’ll be in it for a few weeks, but each sprint ships something real.”

Phase 2 — Richer Stage & Producer-Level Readability

“Make the stage expressive enough that you feel the episode.”

Purpose

Turn the Stage from “it works” to “it tells a story visually.”

The goal is that a Producer can open the viewer, scrub an episode, and say:

“Okay, I see Delta unwind and the floor cools off.”

What it aims to accomplish

Richer visual encodings

Agents:

Stress → size / ring thickness / pulse speed

Guardrail vs context → orbit shape or border style

Incidents → subtle flashes or icon overlays

Stage:

Tension → background gradient / vignette

Story arc → title card / overlay summary

Better navigation

Scrub through days smoothly (animated transitions).

Maybe step through “beats” if we define them.

Agent focus

Click an agent → right panel shows:

Stress arc (start → end)

Short narrative summary (explainer)

Trait snapshot & memory drift lines.

Small quality-of-life improvements

Episode picker with metadata (date, seed, config summary).

Persistent linking: URL that encodes selected episode/day.

Layers touched

stage — may evolve for extra view-friendly fields (e.g. precomputed “stress band” categories).

ui-stage — most work here (animation, UX, visuals).

Concrete deliverables

Stage where:

It is obvious which agent is tense vs calm.

You can tell if tension is rising or falling over the episode.

You can click an agent and read a “psych snapshot” of their arc.

Estimate

2–3 Junie-sprints

Sprint 1: richer encodings for agents + tension

Sprint 2: agent focus panel + smoother transitions

(Optional) Sprint 3: polish, refactors, minor new affordances

🟧 Feels like: “You’ll be building this for a bit,” but each sprint should leave the Stage more usable for real analysis.

Phase 3 — Live Mode & Control Room

“Turn the episode player into a show you can run, not just replay.”

Purpose

Move from “watching past logs” to running live episodes with Producer controls.

This is where the Director and Producer metaphors become literal:

The Producer picks a config.

Loopforge runs a sim.

The Stage shows it in (near) real-time.

What it aims to accomplish

Live episode flow

Add API endpoints to:

trigger a new sim run with config (POST /episodes/run)

expose run status

optionally stream or poll action logs / interim summaries

On the frontend:

“Run Episode” button that:

collects config

kicks off a run

moves to a “live-view” state

Incremental Stage updates

Instead of waiting for full export, Stage receives:

partial day summaries

currently known tension

partial story arc (or live commentary text)

UI:

Agents animate as the run progresses.

Tension meter updates.

Live headline: “Floor is getting sharper / cooling down / holding steady.”

Producer Console (non-LLM first)

Controls for:

supervisor tone (supportive, punitive, detached, mixed)

base tension level

autonomy vs guardrail bias

episode duration (days, steps_per_day)

seed (optional)

Config panel saved as presets.

Glue to existing CLI

You can still run sims via CLI, but Producer Console makes runs accessible from the Stage UI.

Layers touched

core — maybe small hooks for run configs, but no structural change.

psych — ensure supervisor style / weather can be parameterized.

analytics — support incremental summary (if needed).

stage — possibly add incremental-building helper.

api — new endpoints for:

running sims

watching run state (status, progress, partial data).

ui-stage — new “Live” mode + Producer Console UI.

Concrete deliverables

A Producer can:

choose a config in the UI,

click “Run Episode,”

watch an episode unfold with a responsive stage,

then review the completed episode as a normal StageEpisode.

Estimate

3–5 Junie-sprints
(This is the first properly “You’ll be building this for a while” phase.)

Example breakdown:

Sprint 1: run-config plumbing at core/api level, basic POST /episodes/run.

Sprint 2: live polling/streaming + incremental Stage updates.

Sprint 3: Producer Console UX + simple presets.

Sprint 4–5 (optional): performance/polish, resilience, additional visual cues.

🟥 Feels like: “This is a mini-arc, not just a sprint,” but it’s where Loopforge becomes a playable drama machine.

Phase 4 — Cinematic & Multi-Renderer Upgrade

“From dashboard to actual theatre.”

Purpose

Offer a more cinematic representation of episodes without breaking the existing simple StageRenderer.

This phase is triggered when you want to:

impress humans who don’t read logs

use the Stage as a “showpiece” for demos, talks, or even installations

explore more abstract / artistic renderings of robot psychology

What it aims to accomplish

Renderer abstraction

Formalize StageRenderer interface:

StageRenderer2D (existing)

StageRenderer3D (future)

Same props, same StageEpisode, different implementation.

Optional 3D/cinematic layer

Introduce React Three Fiber (Three.js in React).

Implement a first StageRenderer3D:

Agents as floating nodes in 3D space.

Camera & lighting tied to tension/story arc.

Basic scene transitions through days.

Theatre mode vs Lab mode

Theatre mode: 3D, cinematic, dramatic.

Lab mode: 2D, clean, analytic.

Toggle available in UI.

SFX for story arcs

Specific visual patterns for:

“Decompression”

“Escalation”

“Chronic high tension”

Memory drift as short monologue scenes or highlight effects.

Layers touched

stage — may stay mostly unchanged; StageEpisode remains the same.

ui-stage — big changes, but all in the rendering/UX layer.

Concrete deliverables

Option in UI to switch between:

Simple viewer (what analysts will live in)

Cinematic viewer (what demos / talks will use)

No change required on sim side.

Estimate

2–4 Junie-sprints

Sprint 1: renderer abstraction + basic 3D stage.

Sprint 2: tension-driven camera/light + agent presence.

Sprint 3–4 (optional): transitions, advanced FX, polish.

🔴 Feels like: “You’ll be building a small stagecraft system,” but only if/when it’s strategically useful.

Phase 5 — Extended Ecosystem (Optional / Future)

“Turn Loopforge into a platform, not just a show.”

This is “later, if it earns it” territory. Only worth doing if earlier phases prove that the Stage is genuinely insightful and fun.

Possible directions

Episode Library & Tagging

Tag episodes by:

arc type, tension pattern, interesting incidents.

A “Netflix for robot drama” UI:

“Show me episodes where:

Delta’s agency rises and trust falls

tension spikes mid-episode

supervisor is punitive.”

Experiment Configurator

UI for designing experiment batches:

“Run 20 episodes with varying supervisor tones.”

Visualize aggregate patterns on the Stage.

Collaborative Viewing

Shareable links.

Comments/annotations on episodes.

“Director’s notes” pinned to specific days or events.

Installation / Performance Mode

Full-screen, auto-playing episodes.

Ambient mode for galleries, offices, or streams.

Sprints

This clearly drops into “you’ll be building this for a while” territory and will depend on priorities. Think:

4+ Junie-sprints for any non-trivial subset

best approached as independent subtracks once core Stage is solid.

Summary Table — Phase vs Effort
Phase	Name	Main Goal	Rough Junie-Sprints	Feel
0	Stage API Foundations	Canonical StageEpisode + API	1–2	Single-cycle
1	Episode Player v1 (Static Stage)	Basic 2D viewer, day-by-day playback	2	1–2 cycles
2	Richer Stage & Readability	Expressive visuals + agent focus	2–3	Multi-cycle
3	Live Mode & Control Room	Run episodes from UI + live visualization	3–5	Full mini-arc
4	Cinematic Upgrade	3D / theatrical renderer, lab vs theatre mode	2–4	Optional arc
5	Extended Ecosystem	Library, experiments, collaboration, installs	4+	Long-term