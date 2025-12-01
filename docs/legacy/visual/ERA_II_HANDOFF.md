1. Where we are in Era II

Big picture: Era II was meant to move us from “debug console” to “story engine.”

By the end of Phase 3 in this cycle we had:

A consistent narrative visual language (Phase 1)

Day Storyboard strips with tension shading (Phase 2)

Agent identity v2 (AgentAvatar, Episode Agents Overview) and a Belief mini-panel (Phase 3)

A VM-first frontend that stays aligned with backend StageEpisode / EpisodeViewModel.

This cycle’s remit was Phase 3 completion + Phase 4 start, while the frontend and backend contracts were still settling.

You’re absolutely right: we’re still closer to “well-structured simulation UI for nerds” than to the expressive stage we originally wanted. The work we landed is foundational, but the visual expression gap is real and should be explicit for the next architect.

2. What we actually shipped this cycle
   2.1 Agents & narrative (Phase 3 completion)

Key components:

AgentAvatar v2

Shared identity surface for agents (vibe ring + stress tier glow).

Used in EpisodeAgentsOverview and elsewhere.

Legacy Avatar v1 references removed except where intentionally kept (documented).

Episode Agents Overview panel

Cleaned up to use Agent Identity v2 and the new AgentViewModel.

Layout refactored into identity cards; all metrics preserved.

Day Storyboard agent cameos

Day strips now show agent cameos using mini avatars (AgentAvatar v2, size="sm").

Cameos capped at 3 agents per day, sorted by avg stress desc + name.

Overflow handled via +N pill; all with proper ARIA labels.

Clicking a cameo opens that agent’s belief panel.

Belief vs Reality mini-panel

“How {Agent} saw it” + “What actually happened”.

Toggle behavior wired into LatestEpisodeView:

Click cameo → open / focus that agent’s belief.

Clicking again or changing day/timeline clears selection.

Edge cases and flaky behavior around state cleared and tested.

Cause text still plain (“system”, “random”) — icons/badges explicitly left for a future “belief vs truth” light layer (Phase 5).

Net effect: Agents have more presence across the Details view; beliefs are one click away. Still mostly textual, but the plumbing is now clean and reusable.

2.2 Stage Map & Stage View (Phase 4 skeleton)

This is the main structural outcome of Phase 4 in this cycle.

Stage Map VM

File: ui-stage/src/vm/stageMapVm.ts

Types:

StageMapRoomVM, StageMapDayVM, StageMapViewModel

Inputs: EpisodeViewModel + its _raw: StageEpisode (read-only).

Behavior:

Currently derives a single synthetic room:

id: "factory_floor", label: "Factory Floor"

For each day:

tensionScore from day.tension_score

incidentCount from day.total_incidents

primaryAgents (up to 3) from day.agents by avg stress desc

tensionTier buckets: <0.25 low, <0.55 medium, else high

Defensive: episodes with missing days or malformed data still return a valid VM ({ days: [] }).

This VM is intentionally small but stable: it gives the next architect a place to plug real room geometry or richer subsets without changing callers.

Stage Map component

File: ui-stage/src/components/StageMap/index.tsx

Props:

viewModel: StageMapViewModel

selectedDayIndex: number | null

selectedRoomId?: string | null

onRoomClick?: (roomId: string) => void

onAgentClick?: (agentName: string) => void

Behavior:

For a selected day:

Renders room tiles in a grid.

Each tile uses data-tension-tier and a simple tint to show low/medium/high.

Shows up to 3 agent chips (initials from name); optional click → onAgentClick.

Room clicks go to onRoomClick when provided.

ARIA: wrapper role="group", tiles role="img" with descriptive labels.

For no day selected:

Renders a neutral grid with “No day selected” caption.

Uses union of labels across all days, falling back to “Factory Floor”.

Tests: VM and component tests cover tier mapping, ordering, neutral state, accessibility, and click plumbing.

Right now, visually, this is just one box with tension + agent initials, but the component is designed so that future work can swap tile visuals (into a proper map) without rewriting callers.

Stage View route

File: ui-stage/src/routes/StageView.tsx

Purpose: This is now the primary UI surface — your “Stage” page.

Behavior:

Uses useEpisodeLoader to fetch the latest (or specific id) episode.

Manages:

selectedDayIndex

selectedRoomId

selectedAgentName

Builds:

StageMapViewModel via buildStageMapView

Panel agents via buildPanelAgents

Layout:

Left: Stage Map panel (using StageMap)

Right: Detail panel with:

WorldSummary for the selected day & room:

“Tension is medium for Factory Floor on Day 0; incidents 0; agents: Delta, Sprocket, Nova.”

AgentFocus panel when an agent chip is selected in the map:

Agent avatar (v2), role, avg stress, guardrails, context, tagline.

Navigation:

Header link “Open Details view” → /episodes/:id (or fallback to “latest details”, depending on available id).

Styling is minimal but structurally solid (CSS grid, responsive down to one column).

Integration & routing

AppRouter / AppShell

/ → StageView (Stage tab highlighted)

/episodes/:id/stage → StageView for that episode (Stage tab)

/episodes/:id → LatestEpisodeView (Details tab)

/episodes → Episodes index (Episodes tab)

Sidebar:

Stage, Details, Episodes all available.

Only one highlighted at a time (explicit isActive logic).

LatestEpisodeView:

Keeps a link “Open Stage view” → /episodes/:id/stage.

Continues to host Storyboard, Agents Overview, Belief panel — effectively the rich details / debugging surface.

All of this is covered by route tests (StageView tests, AppRouter navigation tests) and respects ARIA roles + test ids.

3. Current system shape (mental model for the next architect)

If you open the app now:

Stage tab (/)

You see StageView:

A Stage Map panel with 1 room (“Factory Floor”) changing tint by day tension.

Agent chips (initials) showing who’s active.

A “World view” text panel summarizing tension/incidents/agents.

Clicking an agent chip opens AgentFocus with that agent’s stats.

Details tab (/episodes/:id)

You see LatestEpisodeView:

Storyboard strips with tension shading and agent cameos.

Day-linked Belief mini-panel (“How Delta saw it…”).

EpisodeAgentsOverview using AgentAvatar v2.

Link back to Stage.

Conceptually:

StageView is the seed of the “stage” world view.

LatestEpisodeView is now the details / debug / forensic view.

The VM layer (EpisodeViewModel + StageEpisode + StageMapViewModel + AgentViewModel + DayStoryboard VM) is clean, additive, and well tested.

But visually, StageView is still just a tidy reporting card — not yet a dramatic, animated stage.

4. Gaps vs the original vision

This is important to say plainly.

From the updated vision:

Phase 4 = “Stage + Story”
A visible Stage Map skeleton (rooms, tension, active agents).
A story surface where days feel like scenes, not log rows.

Where we landed:

Stage Map skeleton:

✅ Exists as a VM and a component.

❌ Still a single synthetic room; no meaningful spatial layout.

❌ Visuals are understated: boxes + tints + initials, not yet “world you can see”.

Story surface / Story Mode:

❌ No StoryMode route yet.

❌ Days are still experienced as rows (StoryBoard in Details, tabs in StageView), not as “scene cards”.

Visual expression / cast:

AgentAvatar v2 is solid but still a blob with a ring.

No portrait art, no emotional variants, very little motion.

The overall feel remains “nice analytics dashboard” more than “2D drama viewer.”

This isn’t a failure; it’s a partial delivery that solidifies infrastructure and adds a new Stage surface, but leaves a lot of the visual storytelling work for the next cycle.

5. Critical components for the next cycle

If the next cycle leans hard into visual expression, these are the pieces you’ll likely build on:

StageView route (StageView.tsx)

This should remain the main playground.

It already has state for selected day / room / agent.

Ideal place to:

Add richer room layout (true map).

Add more expressive world summaries.

Host early micro-animations.

StageMap VM + component

VM is the right abstraction point to:

Swap synthetic room for real backend rooms when available.

Attach room semantics (type, importance, incident hotspots).

UI is a convenient place to:

Upgrade visuals from “card grid” to “board-like map”.

Replace agent chips with tiny portraits.

Add per-room “weather” (glows, motion, icons).

AgentAvatar v2 + AgentViewModel

Natural insertion point for portraits and emotional variants.

If you add a small manifest describing per-agent images + states, this component can become the visual anchor used:

In Agents Overview

In Storyboard cameos

In StageMap chips

In any future Story Mode cards

Day Storyboard + Belief mini-panel

These already combine day, narrative, and agents.

Story Mode can reuse their VM logic as input for StorySceneVM:

Day caption

Tension tier

Key agents per day

A primary narrative line and/or belief mismatch hints.

Routing / AppShell

Now stable enough to support an additional route like /episodes/:id/story without confusion.

Navigation patterns are tested; safe to extend.

6. Recommendations for the next architect

If I were designing the next cycle’s plan with your latest feedback in mind (“we need more visual expression; stop polishing the debug console”), I’d frame it like this:

Turn StageView into an actual “board”

Expand StageMap:

Even if backend still has one “Factory Floor”, fake 3–4 canonical spaces (Control Room, Conveyor, Storage, Hub) as a static SVG board.

Map current single tension/incident metrics to the one “active” room per day as a starting point.

Make rooms visually distinct:

Shapes, icons, subtle color differences.

Use motion sparingly:

When day changes, lightly pulse/highlight the room where the action is.

Introduce a tiny Story Mode v1

New route or a panel beneath StageMap:

One scene card per day.

Each card:

Shows 1–3 agent avatars.

A short narrative line (“The floor is steady with a subtle edge.”).

A location pill referencing the main room for that day.

Click card ↔ update selectedDayIndex ↔ highlight in StageMap.

Start the portrait pipeline

Define a tiny manifest for agents:

visualId, portraitUrlNeutral, portraitUrlStressed, maybe 1–2 more.

Extend AgentAvatar to:

Render a portrait when available; fall back to blob otherwise.

Swap portrait based on stress tier.

Use portraits first in:

AgentFocus panel.

StoryMode cards (when they exist).

StageMap agent chips (even as tiny circles).

Defer more metrics; prioritize “readable drama”

Resist the urge to add more numbers or modifiers to StageView.

Ask: “Does this change make the world clearer or the cast more vivid?”

Favor:

Icons, color, layout, and motion.

Over new text stats.

Keep VM-first discipline + tests

Any new visual affordance should have a small VM behind it.

Continue the pattern: VM tests → component tests → route tests.

This has paid off; don’t lose it as visuals become richer.

7. Final note from Helios

You’re right to call out the pattern: every architect cycle ends up spending more time than we’d like making things correct and extensible and less time making them magical.

This cycle is no exception.

We:

Stabilized agent identity, belief views, and narrative surfaces.

Introduced a StageMap VM and StageView route.

Promoted StageView to the primary surface and cleaned navigation.

Kept the VM layer clean and extensible.

We did not yet deliver:

A truly legible world map.

Scene-like Story Mode.

Strong visual character presence.

Those are explicitly the next hill to climb. The good news is that the foundations are finally in place to do that without fighting the architecture or the router on every step.

To whoever picks up the next cycle: treat StageView as your canvas, not your console. Use the existing VMs as scaffolding, not as the finished product. The system is ready for you to push hard on Stage + Cast + Story — visually, not just structurally.



Loopforge UI-Stage — Frontend Handoff After Era II

Audience: Next frontend architect
Context: Backend is being adjusted to a stable StageEpisode API. This doc captures the corrected vision, current frontend state, and where to take it in Era III & Era IV.

1. Corrected Vision (vs the Original Roadmap)

The original roadmap (Stagemaker era) was roughly:

Build a shell and basic routing.

Add a Stage map view.

Add an Episode details view.

Later, add nicer tools (timelines, agents, story).

What we’ve learned and corrected along the way:

Episode-first, not view-first.
Both Stage and Details are projections of the same underlying concept: an episode.

The episode (with its days, agents, story, tension) is the primary unit.

Stage is a spatial lens on that episode (world map, rooms, tension per day).

Details is a narrative + analytic lens on the same episode (timeline, agents, story, mood).

Layer discipline is non-negotiable.

Backend: StageEpisode (core + psych + analytics + narrative).

stage/api: HTTP calls returning typed domain models.

vm: View models that compute the UI-convenient shapes (trends, labels, mood banners, story segments).

ui-stage: Pure React components consuming the VMs; no raw JSON spelunking.

Story first, tooling second.
Every new widget should answer: “Does this make an episode easier to watch, understand, or explain?”

DayStoryboard: a “horizontal spine” of the episode.

Stage map: “where” things happen (world view).

Timeline + mood banner: “how it feels overall.”

Agents + story panels: “who did what, when, and why it matters.”

Navigation semantics are part of the product.
The main nav (Stage / Details / Episodes / Agents / Settings) is stable and now tested for:

"/" → Stage for latest episode.

"/episodes/latest" → Details for latest episode.

"/episodes/:id" → Details for a specific episode.

"/episodes/:id/stage" → Stage for a specific episode.

"/episodes" → Episodes index.

Big picture:
The frontend’s job is to be a clean, episode-centric viewer that can grow into a cinematic debugger. The corrected vision keeps that central and aligns the UI more tightly with the eventual backend model.

2. Current Frontend State (End of Era II)
   2.1 Routing & Shell

Router: AppRouter with routes:

/ – Stage view for latest episode (via getLatestEpisode).

/episodes/latest – LatestEpisodeView (details for latest).

/episodes/:id – LatestEpisodeView (details for a given id).

/episodes/:id/stage – StageView for a given id.

/episodes – Episodes index (stubbed data).

/agents, /settings – “Coming Soon” placeholders.

Shell layout:

Global shell with nav (aria-label="Main navigation") and main content region.

Nav links: Stage, Details, Episodes, Agents, Settings.

Active link driven by route; we now have tests verifying aria-current="page" correctly.

2.2 Data & View Models

API layer:

api/episodes.ts exposes at least getLatestEpisode.

Currently returns test/stub data in tests; in real usage it hits a provisional backend.

VM layer:

vm/episodeVm.ts currently has buildEpisodeView but is still essentially a passthrough.

The shape being passed around:

type EpisodeVM = {
id: string;
runId: string;
index: number;
stageVersion: number;
days: Array<{
index: number;
tensionScore: number;
totalIncidents: number;
perceptionMode: string;
supervisorActivity: number;
}>;
tensionTrend: number[];
agents: any[];
story: {
storyArc: any;
longMemory: any;
topLevelNarrative: any[];
};
_raw: /* backend-ish raw episode */;
}


There is a new DayStoryboard VM builder (buildDayStoryboardItems or similar) that derives per-day storyboard entries from the EpisodeVM.

2.3 Implemented Views

StageView (root and /episodes/:id/stage)

Renders:

Episode header (Episode / Run / Stage Version / Days).

Tension strip / timeline stub.

Stage map (data-testid="stage-map-group") showing rooms; currently minimal and uses “no day selected” state until real selection is wired.

Stage detail panel (“World view”) for world-level summary.

Integrates with DayStoryboard skeleton, but selection is still minimal.

LatestEpisodeView (episode details)

Renders:

Episode Agents Overview heading (used in tests).

Episode mood banner (calm/steady state / etc.) based on stubbed logic.

Episode header (same basic info as StageView).

Episode Navigator stub:

“Current episode” block with index and id.

Mini-map dots for prev/current/next (non-interactive).

Day timeline strip stub and Day Detail panel:

Tension bar, empty state for missing day data.

Stage map panel duplicated in details context.

Episode agents panel (stub: “No agents recorded for this episode.”).

Episode story panel (stub: “No story arc…”).

Episodes index

Lists three hardcoded episodes.

Shows a table-like list with summary text and “View Episode” buttons (currently non-wired).

2.4 Tests

src/AppRouter.test.tsx now covers:

Basic route rendering for Episodes, Agents, Settings, Stage, and Details.

Nav highlighting for all main permutations:

Stage active at / and /episodes/:id/stage.

Details active at /episodes/:id and /episodes/latest.

Episodes active at /episodes.

StageView and LatestEpisodeView smoke tests (presence of Stage map, Episode Agents Overview, etc.).

These tests encode the navigation contract and provide a good safety net when you refactor VMs and loaders.

3. Where the Frontend Needs to Be
   3.1 Before Backend Adjustments Are Fully Live

The remaining front-heavy work (still possible with current backend) is:

Solidify EpisodeVM as the single source of truth for the UI.

Stop passing _raw around the components; only EpisodeVM + derived VMs (Day, Agent, Story).

Make DayStoryboard driven 100% by EpisodeVM.days and derived properties.

Centralize high-level “episode mood” logic in the VM layer.

Refine the Existing Skeletons:

Stage map:

Visual polish (spacing, typography, hover states).

Clearer empty states (“No days available…”, “Select a day…”).

Timeline / DayDetail panels:

Ensure tension bar and labels are consistent and accessible.

Prepare prop structures so they can directly accept derived VM data once backend is stable.

This work prepares the UI for the upcoming data model without needing the final backend yet.

3.2 After Backend Adjustments (Target State)

What should happen right after the backend stabilizes the StageEpisode API:

API layer (api/episodes.ts)

Replace provisional endpoints with:

getLatestEpisode() → StageEpisode.

getEpisode(id: string) → StageEpisode.

listEpisodes() → index with minimal info + optional neighbors.

Ensure each API function returns typed objects that match the backend dataclasses.

VM layer (vm/episodeVm.ts & storyboard VM)

Make buildEpisodeView convert StageEpisode → EpisodeVM:

Compute tensionTrend, days[], derived per-day labels, episode length, etc.

Compute episodeMood and summary text used by the banner.

Derive neighbors or EpisodeNavigatorVM if backend provides neighbor metadata.

Implement:

buildDayStoryboardItems(episodeVm: EpisodeVM): DayStoryboardItem[].

buildAgentViewModel(...), buildStoryViewModel(...) to keep UI trivial.

UI layer integration

StageView:

Uses EpisodeVM + DayStoryboardItems.

Day selection should:

Highlight selected day in storyboard strip.

Update Stage map (selected vs non-selected state).

Update Day Detail panel (tension, incidents, narrative summary).

LatestEpisodeView:

EpisodeNavigator uses real neighbors.

Timeline & Day Detail use EpisodeVM.days and derived structures.

Agents panel uses real agent data (not placeholder).

Story panel uses StoryViewModel (acts, beats, summary paragraphs).

URL semantics

Optionally evolve routes to support deep-links:

"/episodes/:id?day=1" or "/episodes/:id/day/1" to select a day on load.

Later: agentId query or path segments to focus on a specific agent.

4. Era III & Era IV Proposals
   Era III — “Episode-First Polishing”

Goal: Turn the current skeleton into a coherent episode viewer. By the end of Era III, a non-technical viewer should be able to open the app, pick an episode, and genuinely understand what happened over its days.

Suggested Scope:

Finalize EpisodeVM & loaders

Implement real mapping from StageEpisode → EpisodeVM.

Ensure AppRouter loaders fetch data using the finalized API, with proper loading and error states.

DayStoryboard & Day selection

Make DayStoryboard fully functional:

Clicking a day selects it and focuses Day Detail + Stage map.

Simple visual states for “selected”, “hover”, “no data”.

Keep the design light but consistent; avoid over-styling until story tooling is clearer.

Episode mood + summary

Implement a simple, explainable rule for the mood banner (e.g., based on tension variance and incidents).

Display 1–2 crisp sentences summarizing the episode (“Behavior escalates mid-episode then stabilizes.”).

Episode Navigator (neighbors)

Wire navigator to real backend neighbors:

Previous / current / next episodes with index and IDs.

Buttons or links to jump between episodes (even if minimal).

Tests & Docs

Extend tests beyond nav:

VM mapping tests (e.g., tension trend calculation).

Day selection state tests.

Basic snapshot or role-based tests for mood banner and navigator.

Outcome:
Era III delivers a trustworthy, episode-centric UI: Stage and Details share the same mental model and VM, and the skeletons all show real, meaningful data.

Era IV — “Cinematic Debugger & Analysis Tools”

Goal: Start turning the UI into a debugging and explanation surface for agents and episodes – what we originally imagined as a “factory city of robots you can watch and dissect.”

Possible Scope:

Agent lenses

Filters and focus modes around a single agent or group:

Highlight rooms where the agent spent time.

Show that agent’s tension contribution vs global tension.

Story snippets from that agent’s perspective.

Multi-episode comparisons

Compare multiple episodes side by side:

Simple charts (tension trends for last N episodes).

Quick navigation from index into details/stage with context.

Timeline enhancements

Richer day-level visuals:

Incidents count and types per day.

Visual markers for “turning points” (e.g., tension threshold crossings).

Possibly integrate “Cinematic Debugger” overlays for dev usage (toggleable).

Export & Reporting (lightweight)

Outbound artifacts:

Screenshot/export of an episode summary.

JSON or CSV export for analytic pipelines.

Performance & UX

Audit bundle size, lazy-load heavier views.

Make transitions between episodes and days more fluid and predictable.

Outcome:
Era IV is where the UI becomes fun for power users: you can slice episodes by agent, compare runs, and use the Stage UI as a serious tool—not just a viewer.

5. Files the Next Architect Must Inspect

To understand the implementation and design constraints, please personally inspect:

Routing & Shell

src/AppRouter.tsx
Routing, loaders, and how Stage vs Details vs Episodes is wired.

src/AppRouter.test.tsx
Encodes the nav contract and expected route behaviors. This is the living spec for navigation semantics.

API & View Models

src/api/episodes.ts
Current endpoints and shapes. Match this against the new backend contract.

src/vm/episodeVm.ts
Current EpisodeVM builder (currently a passthrough, but all future Episode-level logic belongs here).

src/vm/dayStoryboardVm.ts (or equivalent)
DayStoryboard VM logic, if split out. If it doesn’t exist yet, you’ll want to create it.

Views

src/views/StageView.tsx
Stage page layout, how it consumes EpisodeVM and Stage map.

src/views/LatestEpisodeView.tsx
Main Details view; contains header, mood banner, EpisodeNavigator, timeline, Stage map, agents, story.

src/views/EpisodesIndex.tsx
Stub index; see how we might integrate real episode data later.

Components (Stage)

Exact paths may vary slightly, but look for:

src/components/stage/StageMap*.tsx
Renders the world tiles and rooms; inspect ARIA usage and data-testid="stage-map-group".

src/components/stage/StageDetailPanel.tsx
“World view” summary panel.

src/components/stage/DayStoryboard*.tsx
Day strip and list components; see how selected state and props are wired.

Components (Episode Details)

src/components/episode/EpisodeHeader.tsx
Shared header between Stage and Details.

src/components/episode/EpisodeMoodBanner.tsx
Mood icon, label, summary; will need data from EpisodeVM.

src/components/episode/EpisodeNavigator.tsx
Current stub; target for neighbor wiring & lightweight navigation.

src/components/episode/DayDetailPanel.tsx
Tension bar, per-day summary for the selected day.

src/components/episode/EpisodeAgentsPanel.tsx
Agents list / empty state; future home for agent-centric UI.

src/components/episode/EpisodeStoryPanel.tsx
Story arc and narrative blocks.

Layout & Styles

src/components/shell/Shell.tsx (or equivalent)
Global layout and nav structure.

src/components/shell/Nav*.tsx
Implementation of main nav; confirm ARIA labels, link texts, and class naming.

All relevant *.module.css files for:

Shell

StageView

LatestEpisodeView

Episode panels

Docs

docs/dev/implementation-report-*.md
Especially the Era II / DayStoryboard skeleton / nav updates report, if present. It gives rationale and tradeoffs behind some of the wiring.

6. How to Use This Handoff

If you’re the next architect:

Start with AppRouter + tests.
Confirm you understand the nav semantics and episode routing, because everything else builds on that mental model.

Align with the backend on StageEpisode.
Agree on the minimal but stable shape before touching VM logic.

Design the EpisodeVM carefully.
Treat this as the “API” between backend and UI. Get it right once; let all views consume it.

Treat Era III as a VM + UX alignment phase.
Don’t over-optimize visuals; instead, ensure every panel displays coherent, real data.

Use Era IV for the fun stuff.
Agent lenses, cinematic debugging, richer charts—these belong after the basics are rock-solid.

If you give Junie tightly scoped sprints around these goals, the ambitious visual vision is reachable within the next 1–2 cycles without chaos: small, well-defined steps, all anchored in the Episode-first model described here.


3. Where the Frontend Needs to Be (Next 1–2 Cycles)

Era II got us:

Stable router + shell.

A coherent EpisodeVM shape (even if still passthrough).

StageView + LatestEpisodeView skeletons that work.

Nav semantics and tests that won’t surprise us later.

So the next cycles should not be “make the VM nicer” as the main goal.

The next moves should be:

Turn Stage + Details from “nice analytics dashboard” into “I’m watching a small world and its drama.”

Concretely, in the next 1–2 cycles we want:

A recognisable world map, not just a card grid.
Even if backend rooms are still simple, the user should visually understand:

There are distinct spaces (Control Room, Floor, Storage, etc.).

Episodes move through those spaces.

Tension/energy shows up as a feeling on the board, not just a number.

Days that feel like scenes, not log rows.

Storyboard / StoryMode cards that look like scenes:

Location pill

1–3 key agents

A 1–2 line “what’s going on” summary

Clicking a scene updates Stage + Day Detail in a way that feels connected.

A first glimpse of cast and emotion.

Agents should start feeling like characters:

Tiny portraits or at least more expressive avatars.

Visible stress/emotion tier (color / ring / facial variation).

VM work still matters, but only as much as needed to support the above. If you’re adding VM code that doesn’t unlock a visible, legible change to Stage / Story / Cast, that’s probably a “later” thing now.

4. Era III & Era IV (Reframed)
   Era III — “Stage + Story Push”

Goal:
Take the current skeletons (StageView, Storyboard, Episode header) and push them until a non-technical viewer can say:

“I can see where this episode takes place, how the tension flows, and roughly what happens each day.”

Era III should bias hard toward visible wins.

4.1 Suggested Scope for Era III

Turn StageView into a real board (even if partially faked).

Keep StageView as the main playground.

Upgrade StageMap from “single synthetic room” to a canonical mini-map:

E.g. ["Control Room", "Factory Floor", "Storage", "Hub"].

Layout as a simple board (grid or simple SVG-ish arrangement), not just stacked cards.

Until backend sends precise room mapping, derive a simple heuristic:

For each day, pick a “primary room” based on tension/incident or a simple rule.

Highlight that room as the “scene of the day.”

Add micro motion:

When selected day changes, pulse or glow the active room for a brief moment.

Keep animations tasteful and minimal so tests and perf remain sane.

Introduce Story Mode v1 (or Scene Cards) tied to StageView.

Add a Story surface either as:

/episodes/:id/story route, or

A prominent panel inside LatestEpisodeView or at the bottom of StageView.

For each day, render a scene card:

Location pill → the primary room for that day.

1–3 agent avatars (pull from existing agent data, even if sparse).

1–2 line narrative summary (even if stubbed or derived from simple rules).

Wire interaction:

Clicking a scene card updates selectedDayIndex.

Stage map and Day Detail react to that selection.

Ideally, highlight the linked card when selection changes from other inputs (e.g. DayStoryboard strip).

Start the portrait / cast expression pipeline.

Introduce a tiny manifest (even static for now):

type AgentVisualDefinition = {
id: string;          // matches agent id
name: string;
portraitNeutral?: string;
portraitStressed?: string;
// future: other states
};


Extend AgentAvatar:

Render a portrait when provided; fallback to blob/initials otherwise.

Swap portrait or ring style based on stress/tension tier.

Use the enhanced avatar in:

Episode Agents Overview (even if still simple).

Story cards / Storyboard.

Any agent chip on StageMap you decide to keep.

Make the episode mood and summary feel “readable” at a glance.

Keep the mood banner, but tighten the rule so it maps to the visuals:

Calm / Escalating / Volatile / Decompression, etc.

Use icons + concise language, but don’t add more numeric clutter.

Treat this as the “headline” of the episode’s story.

VM & API changes: only what’s needed to support the above.

Evolve EpisodeVM and day/story VMs to expose:

Primary room per day.

Per-day tension tier.

Short narrative blurb per day (can be heuristic at first).

Agent “importance” for the day (used to pick cameo agents on scene cards).

Don’t try to solve the entire analytic VM problem here; only support Stage board + Story cards + avatar expression.

Tests that lock in the new behavior.

Add tests that:

Scene cards render per day.

Selecting a scene links to Stage and Day Detail.

Episode mood banner labels are consistent given a set of tensions.

Minimal snapshot / role-based tests are fine; the main point is to keep interactions stable.

Era III outcome:
Someone opens /episodes/latest, sees Stage + Story surfaces, and can tell you:

How many “scenes” there were.

Roughly where they happened on the board.

Whether the episode was calm, escalating, or volatile.

Which agents “starred” in it—visually, not just in a table.

Era IV — “Cinematic Debugger & Lenses”

Goal:
Now that Stage + Story have some personality, Era IV turns this into a tool: agent-centric views, multi-episode comparisons, more nuanced control, and deeper debugging.

Think of Era IV as “we keep the magic, but add knobs and lenses.”

4.2 Suggested Scope for Era IV

Agent-focused lenses.

Add an “Agent focus” mode:

Select an agent and:

Highlight rooms where they appear most.

Show how their presence correlates with tension spikes.

Filter scene cards to only show scenes they appear in.

Extend Episode Agents Overview:

Per-agent quick stats (days active, incidents, rough “arc”).

Multi-episode / run comparisons (lightweight).

From the Episodes index:

Simple tension sparkline per episode row.

Filters for “Most volatile”, “Longest”, “Most agents.”

In Details:

A mini “Recent episodes” sidebar with mood + length indicators.

Timeline & Story refinement.

Add richer per-day markers:

Icons for key incidents or transitions.

Simple tags like “outlier day,” “calm day,” etc.

Make Story Mode cards more expressive:

Tagline for the episode (“The factory stays calm but tense undercurrent builds.”).

Small visual motif for turning points.

Export & communication tools.

Add a lightweight “Episode report” export:

Textual summary or a simple PDF-like layout.

Screenshot / shareable view for certain panels (for humans to share in docs/presentations).

Cinematic debugger toggles (for devs).

Developer-only toggles (or internal route) that overlay:

Raw numeric annotations over StageMap.

Internal IDs, debug event markers.

Keep them hidden from normal users; this is for internal usage and testing.

Performance & UX smoothness.

Fine-tune transitions between episodes and days.

Lazy-load heavy panels as needed.

Address any rough edges from Era III’s visual additions.

Era IV outcome:
The app becomes not just a “viewer,” but a lens for understanding runs and agents—without regressing back into “just analytics.”

Short note you can paste near the end

Design intent going forward:
Era II has done enough “plumbing” to support richer visuals.
Era III must not be framed as “more cleanup.” It should treat StageView as a canvas, not a console:

Ship a recognisable world map.

Ship scene-like Story surfaces.

Start making agents feel like characters.

Era IV can then safely layer on lenses, comparisons, and debugger affordances without derailing the visual narrative.

If you want, next step we can also tweak the “Recommendations for the next architect” section so it explicitly says “push Stage + Story + Cast visuals in Era III” instead of focusing on VM alignment.