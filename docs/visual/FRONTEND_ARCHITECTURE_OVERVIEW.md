🌆 Loopforge UI-Stage — Frontend Architecture Overview (End of Era I)

Status: Stable, test-complete, VM-driven, ready for Era II
Scope: ui-stage/ package
Audience: Future maintainers & next architects

1. Philosophy & Design Principles

The UI-Stage frontend is built on a strict set of principles to ensure reliability, predictability, and safe iteration during future expansion:

1.1 UI Never Reads Raw Backend JSON Directly

ALL backend JSON is transformed into explicit View Models (VMs) before rendering.

1.2 Every Component Has a Single Responsibility

Not “God components.”
Panels do one thing:

show agents

show tension

show narrative

show header metadata

show the episode timeline

1.3 UI Must Be Entirely Testable Without Backend

We enforce:

deterministic data

no network calls inside components

no hidden global state

1.4 Code Is Optimized for Future Evolution

The Era I UI is intentionally:

minimal

unopinionated in styling

modular

easy to replace

This prepares the groundwork for Era II’s visual expressiveness layer.

2. Repository Structure (UI-Stage)
   ui-stage/
   │
   ├─ src/
   │   ├─ api/              → mock API interfaces, fetchers
   │   ├─ components/       → all UI components & panels
   │   ├─ hooks/            → data loaders (useEpisodeLoader)
   │   ├─ routes/           → pages mounted under React Router
   │   ├─ utils/            → color maps, utilities
   │   ├─ vm/               → VIEW MODEL LAYER (critical)
   │   ├─ types/            → Type definitions (StageEpisode, blocks…)
   │   └─ AppRouter.tsx     → routing config
   │
   ├─ public/               → static assets
   ├─ tests/ (implicitly in src/*) → co-located Vitest tests
   └─ ...

3. Data Flow — How an Episode Reaches the UI

This is the single most important concept.

3.1 Backend → Raw StageEpisode JSON

The backend emits the canonical episode data structure:

StageEpisode {
episode_id,
run_id,
episode_index,
tension_trend,
days[],
agents{},
narrative[],
story_arc,
long_memory
}

3.2 Raw Episode Is Fed into View Models

VMs rewrite raw data into frontend-friendly shapes:

EpisodeViewModel {
id,
runId,
index,
tensionTrend,
agents[],
days[],
story{...},
_raw: StageEpisode
}

3.3 Components ONLY Receive VMs

Panels never inspect _raw.* except in tests.

4. Core Components (Era I End State)
   4.1 LatestEpisodeView

Primary episode viewer.

Responsibilities:

fetch current episode

coordinate child panels

manage loading/empty/error states

host EpisodeNavigator

Composition:

EpisodeHeader

TimelineStrip

EpisodeAgentsOverview

DayDetailPanel

4.2 EpisodeHeader

Shows:

episode index

run id

story arc summary (placeholder for now)

4.3 EpisodeAgentsOverview

Shows all agents:

avatar initial

role

stress dot (stressColor)

guardrail/context badges

sparkline placeholder for future visual evolution

Extremely future-expandable.

4.4 DayDetailPanel

Renders the detailed breakdown for a single day:

tension bar

summary line

narrative section (via NarrativeBlock)

agents active that day

day metadata (incidents, supervisor activity)

This is a functional placeholder intended to evolve into a richer story representation.

4.5 NarrativeBlock

Atomic narrative renderer.
Handles:

text

kind

tags

day index

agent attribution

This is the proper primitive for future narrative visualization (color coding, icons, clustering, animations, etc).

4.6 TimelineStrip

Episode-level tension summary

tiny bars

tooltips

future expandability for multi-lane tracks

4.7 EpisodeNavigator

Handles:

forward/backwards episode navigation

integration with /episodes/:episodeId route

tests for stable UI navigation behavior

4.8 EpisodesIndexView

Light scaffolding only:

heading

list of episodes

“view episode” button

empty state

stable selectors / semantic list

not intended to be a beautiful page (Era II will likely redesign)

5. Hooks & API Layer
   useEpisodeLoader

A robust, predictable episode loader hook.

Behaviors:

episode → loading → error states

logs debug output for router freeze debugging

tests simulate success/error paths

deterministic behavior used by all page-level views

This is the correct abstraction level for moving into Era II.

6. Routing Architecture

Routing is kept minimal:

/
└── /episodes
├─ index → EpisodesIndexView
└─ /:episodeId → LatestEpisodeView


Notes:

The router is intentionally simple

Nothing nested

No loaders yet

No transitions

Future eras can safely introduce richer routing or React Router v7 features

Tests protect route behavior & navigation

7. View Model Layer (Critical)
   Directory:

ui-stage/src/vm/

This layer transforms StageEpisode data into UI-ready structures.

VMs implemented:

episodeVm

dayVm

dayDetailVm

daySummaryVm

agentVm

storyVm

Era I guarantees:

all VMs have full test coverage

VMs can evolve without breaking UI

the UI depends ONLY on VMs

Era II must extend VMs to support richer narrative structures.

8. Test Strategy

All tests live alongside implementation files.

Test Rules Adopted in Era I:

Prefer role/text/label queries, NOT CSS classes

Snapshot only for textual content

Avoid layout-based selectors

Ensure loading / empty / error states are tested

Each panel has:

smoke tests

component tests

narrative/malformed-data tests

story arc tests (currently minimal)

Stability Guarantees:

The test suite is intentionally broad, shallow, and future-tolerant.
Era II can refactor UI without massive test breakage.

9. Styling Architecture (CSS Modules)

Era I CSS is:

minimal

close to the component

future-replaceable

expressive enough for immediate usability

intentionally not a full design system

Era II is free to:

introduce tokens

introduce motion specs

switch to a design system

unify spacing/typescale

CSS modules are a safe starting point and easy to extend or replace.

10. Current Limitations (Expected)

These are intentional constraints, not failures:

❌ Story arc panel is placeholder
❌ No agent identity view
❌ No relationship graphs
❌ No mind inspection
❌ No expanded narrative timeline
❌ No beat clustering or sequencing
❌ No watch-mode / cinematic transitions
❌ No event-level detail pages

Era I built the skeleton — Era II builds the story.

11. Future Evolutions (High-Level Guidance)
    11.1 Expand NarrativeBlock into a rich storytelling unit

Add:

icons for event types

colors per narrative mood

cluster grouping

beat transitions

expandable metadata

micro-animation of tension

11.2 Redesign DayDetailPanel into a storyboard page

Not a list.
But a visual timeline of beats.

11.3 Multi-lane TimelineStrip

E.g.:

tension lane

supervisor lane

agent stress bursts

conflict spikes

relationship changes

divergence lane

11.4 Agent Focus Mode

Dedicated pages for each agent:

identity

long memory

belief heatmap

stress evolution

attribution chains

11.5 Episode Story Mode

Scrolling narrative with:

day separators

beat cards

visual tension bands

characters highlighted

11.6 Belief–Truth Divergence Visuals

Critical for storytelling.

11.7 Motion & Transitions

Used sparingly but effectively:

tension pulses

rising/falling arcs

beat-to-beat transitions

“camera roll” episode view

12. Summary for New Contributors

This frontend is:

✔ clean
✔ modular
✔ fully tested
✔ view-model-driven
✔ minimal and stable
✔ designed for heavy future transformation

Era I intentionally avoided complexity so Era II can now evolve the narrative layer without tearing down the foundation.

The next architect should start with:

View Models → understand the true data

LatestEpisodeView → understand page composition

TimelineStrip → understand episode-level structure

DayDetailPanel + NarrativeBlock → understand story beats

EpisodeAgentsOverview → understand agent rendering

Everything else can be replaced, removed, or rebuilt during the narrative expansion era.