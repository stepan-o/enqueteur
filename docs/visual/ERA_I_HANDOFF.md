🌇 LOOPFORGE — STAGE ARCHITECTURE HANDOFF DOC (v1.0)

From: Architect Cycle (You + Junie)
To: Next Stage Architect
Era I → Era II Transition Document

1. Long-Term Vision of STAGE

(Foundational orientation — the “north star”)

Stage is the narrative lens for Loopforge.

It exists to translate the simulation (core + psych + analytics) into a coherent narrative experience.

Not a dashboard.
Not a JSON inspector.
Not a debugger window.

But:

A visual story engine showing what agents felt, believed, misinterpreted, and acted on across time.

The final state Stage should evolve toward:

Watchable episodes that read like a storyboard, comic, or documentary timeline.

Belief–truth divergence maps: where the player can literally see how wrong or correct each agent’s worldview is.

Tension as a visual medium, not just numbers or bars.

Agents with personalities, roles, emotional arcs, biases, and memory patterns that feel alive.

A multi-layer viewer:

Day-level beats

Episode-level arcs

Agent-level long-term narratives

Run-level evolution across multiple episodes

The simulation changes the world;

Stage explains the world.

2. Era Structure — How We Intended to Reach the Vision
   Era I — Foundations & Stability (COMPLETED)

Goal:

Build the minimum operational skeleton of the Stage frontend with stable data structures, predictable components, and clean testable patterns.

Output:

Every major panel implemented as a simple, reliable box.

No advanced visualizations yet.

Max stability → min complexity.

Era II — Narrative Expressiveness (NEXT architect)

Goal:

Turn the UI from “panels and boxes” into expressive narrative visual language.

Output will focus on:

real-time narrative flows,

event beats,

character identity and emotive states,

belief–truth deltas,

storyboarding primitives.

Era III — Interactive Exploration

Goal:

Let users explore agent minds, past episodes, and long-memory dynamics through collapsible/expandable storytelling layers.

Era IV — Cinematic Layer (“Watch the Simulation”)

Goal:

A viewer mode that visually animates beats and story arcs as a watchable episode.

3. What Era I Accomplished (Summary of Real Deliverables)

Era I delivered exactly the correct foundation for Era II:

3.1 Core UI Panels Implemented

LatestEpisodeView

EpisodeHeader

EpisodeAgentsOverview

DayDetailPanel

NarrativeBlock component

TimelineStrip

EpisodeNavigator

EpisodesIndexView

Basic StoryArc panel

3.2 Canonical Visual Language v0.1

tension bar (correctly normalized + safe)

stress dot + stressColor

badges (guardrails/context)

avatar initials

narrative block micro-format

simplified day summary

3.3 Complete Test Infrastructure

100% panel-level test coverage

snapshot guards for critical areas

stable selectors

vm-level tests to lock shape

regression guards for loading/empty-states

zero coupling to backend logic

3.4 Unification of Episode → VM → UI contract

Era I established the correct direction:

Raw StageEpisode → view models → UI components
with no direct JSON poking inside React components.

3.5 No dead-end complexity

Crucially, we did not prematurely build:

graph visualizers

AI panels

nested timelines

mind inspectors

expandable agent cards

heavy CSS frameworks

complicated routers

Everything is still light, clean, and forward-compatible.

4. How Era I Enables Era II

Era II is the natural continuation:

With Era I, the next architect now has:

a solid episode viewer backbone

stable test scaffold

stable type contracts

clean UI composition patterns

atomic narrative components

a safe playground for more expressive design

Era I intentionally ended “one step before” anything high-concept.
Era II can now safely reimagine how the story is presented because:

The skeleton is correct.
The data contract is correct.
Nothing brittle remains.

5. What Era II Should Build (Next Architect’s Mission)

This is the hand-off brief for Era II.

5.1 Rich Visual Narrative Layer

Introduce:

narrative clustering (beats, tensions, thematic arcs)

per-agent flame graphs (stress or belief delta arcs)

emotional bursts (localized spikes)

expressive color bands

timeline lanes, multi-lane tracks, mini-maps

Goal:
Make tension and agent behavior visually readable at a glance.

5.2 Episode Storyboarding Mode

A “story mode” like:

comic panels

beat-by-beat cards

scroll-driven transitions

grouped beats (“Act I, Act II…”)

This will transform the episode into a storytelling artifact, not a list.

5.3 Agent Identity Panels

Small but expressive:

portraits (generated or symbolic)

emotional state dots

long-memory traits

biases

recent attributions

relationship graph (lightweight)

5.4 Belief–Truth Divergence Views

One of Loopforge’s core themes.

Add:

what the agent thought happened

what really happened

their attribution

their emotional state

“confidence level” indicators

5.5 Making the UI Feel Alive

Consider:

micro-animations for rising tension

soft pulses for supervisor events

narrative tags with color-coded moods

transitions between days

5.6 Navigation Evolution

move from “episode index → episode viewer” to
“episode timeline → episode layers → agent focus mode”

6. What is UNFINISHED / UNPOLISHED in Era I (Honesty Section)
   6.1 StoryArc panel is placeholder

But correctly isolated so Era II can replace it entirely.

6.2 DayDetailPanel is functional, not expressive

Future architect should refactor for expressiveness, not tweak forever.

6.3 AgentsOverview is visually stable but conceptually shallow

No identity, no complexity yet.
This is expected.

6.4 EpisodesIndexView is intentionally simple

Do not beautify it in Era II unless needed.
It is infrastructure, not core narrative.

6.5 CSS modules are minimal

Era II may convert:

some to tokens

some to variables

some to motion specs

But only where needed.

6.6 Layout and theming are still pragmatic v0.1

Era II can introduce:

better whitespace rhythm

typography scale

iconography set

But avoid perfectionism — it’s unnecessary until content types stabilize.

7. What NOT to Waste Time On in Era II
   ❌ Perfecting the Episode Header

It will likely change once the story arc panel evolves.

❌ Spending time polishing empty states

They are placeholders.

❌ Rebuilding components that will be animated later

Wait until narrative motion spec exists.

❌ Beautifying mock pages (“EpisodesIndexView”)

It is intentionally utilitarian.

❌ Improving tests for components that will be redesigned

Keep tests smoke-level until UI stabilizes.

❌ Adding more UI plumbing before narrative patterns are defined

First define the story → then the UI.

8. Files the Next Architect MUST Inspect Before Proposing a Roadmap

These must be personally reviewed:

8.1 View Models (critical)

ui-stage/src/vm/*

This is the true contract for UI.
Before designing new UI or visual patterns, understand the VM shapes.

8.2 Types (StageEpisode & children)

loopforge-core → types/stage.ts

Otherwise the architect will misinterpret the data model.

8.3 LatestEpisodeView

This is the anchor page.
Era II’s narrative flows will hook into this.

8.4 DayDetailPanel & NarrativeBlock

Baseline narrative rendering.

8.5 EpisodeAgentsOverview

Foundation for future expressive agent cards.

8.6 TimelineStrip

Era II will likely extend this the most.

8.7 EpisodeNavigator & Router Setup

Must understand navigation constraints before adding modes.

8.8 Back-end Episode JSON samples

Inspect actual artifacts.
Architect decisions depend 100% on understanding real episode data.

9. Architect Brief Summary (TL;DR)

Era I gave you the correct skeleton.
It is stable, tested, expressive-enough, and intentionally minimal.

Your Era II mission is to evolve the UI from “functional panels” to
expressive narrative visualizations that let users experience episodes, not read them.

Focus on:

narrative expressiveness

visual storytelling

emotional and belief layers

agent identity

tension and arc visualization

Do NOT spend time polishing placeholders.
Do NOT redesign infrastructure that already works.

Start by inspecting: VM layer → type shapes → LatestEpisodeView → TimelineStrip → DayDetail → EpisodeAgentsOverview.

Everything else should be reconsidered only after you propose the Era II narrative design spec.