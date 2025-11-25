🌇 ERA II — BROAD SPRINT PLAN
“From Functional Panels → Expressive Story Engine”

Era II is organized into four major arcs, each producing visible narrative gains.

⭐️ PHASE 1 — Establish the Narrative Visual Language (Base Expressiveness)

Sprint Goal: Move from “boxes and lists” to an expressive 2D storytelling language.

🔧 Technical Deliverables (Junie)

Introduce narrative visual tokens:

color palette for stress / tension / attribution

subtle motion specs (hover, pulse, fade)

whitespace + typography rhythm v1

Implement NarrativeBlock 2.0:

micro-panels

icons based on kind (beat/recap/aside)

soft mood shading

Integrate new block style into:

DayDetailPanel

Top-level narrative (episode header)

StoryArc placeholder

🎨 Founder tasks

Approve the visual prototypes (simple sketches / mock-ups).

Approve color & mood reference sheet (5 min review).

Review stress/tension color mapping (pick intensity behavior).

✔ Output of Phase 1

A coherent visual style that everything in Era II will follow.

⭐️ PHASE 2 — Day Storyboard Strips (The Real Heart of Era II)

Sprint Goal: Each day becomes a scene, readable as a horizontal narrative strip.

🔧 Technical Deliverables (Junie)

Build DayStoryboard component:

horizontal layout

tension shading behind the strip

mini sparkline (one per day)

narrative blocks rendered in a logical sequence

Integrate day strips into:

LatestEpisodeView

TimelineStrip hybrid view

Implement smooth navigation:

scroll → auto-highlight day

day click → day detail expansion

🎨 Founder tasks

Provide design approval on:

strip composition

sparkline style

block spacing

If desired: provide a mood reference (“comic? documentary? logbook?”)

✔ Output of Phase 2

Browsing an episode now feels like reading a storyboard, not a CSV table.

⭐️ PHASE 3 — Agent Identity & Expression Layer

Sprint Goal: Agents become characters.

🔧 Technical Deliverables (Junie)

Implement AgentCard v2:

avatar derived from visual (procedural)

vibecolor ring

stressDelta glow

attribution icon cluster

tagline reveal on hover

Integrate AgentCard v2 into:

EpisodeAgentsOverview

Agent cameo slots inside DayStoryboard strips

Build Belief-Attribution mini-panel:

shows what the agent thought happened

shows what actually happened

small delta indicator

(Accessible with one click, but minimal.)

🎨 Founder tasks

Approve avatar generation style (options provided).

Provide short descriptive adjectives (optional) to tune vibe → color mapping.

✔ Output of Phase 3

Agents have presence, personality, recognizable patterns — the “cast” is born.

⭐️ PHASE 4 — Episode Story Mode (Era II’s Final Transformation)

Sprint Goal: Allow users to “read” an episode vertically, like a crafted narrative artifact.

🔧 Technical Deliverables (Junie)

Create EpisodeStoryMode route:

top-level narrative as title cards

longMemory nodes

story_arc clusters

chained storyboard strips

seamless vertical scroll transitions

Build chapter markers:

Day 0 → Day N as “scenes”

Episode summary at top

Episode closing card

Add lightweight cinematic transitions:

fade between chapters

tension pulse on chapter entry

scroll-sync shading

🎨 Founder tasks

Approve the story mode vibe:
documentary, graphic novel, minimal logbook, or hybrid.

Optional: contribute writing for episode-summary templates (the showrunner voice).

✔ Output of Phase 4

A complete episode reads like a story — not data.

This is the Era II “end state vision.”

⭐️ PHASE 5 (Optional / Only if time allows) — Belief vs Truth Light Layer

This is not full divergence mapping (Era III feature).
This is a light-touch overlay to prep for next era.

Examples:

A small diagonal “misalignment bar” on each agent cameo.

Tiny indicators on days where attribution was wrong.

Optional highlights on beats with unmet expectations.

🎨 Founder tasks

Approve minimal visual direction (tiny iconography).

✔ Output of Phase 5

Era III will be able to layer cognition on top without reworking the Era II structure.

🎬 Era II — Desired Final State (Definition of Done)

By the end of Era II, Loopforge should:

✨ 1. Feel like a narrative engine

Episodes present themselves as story sequences, not logs.

🎨 2. Contain expressive 2D visual identity

Mood-based colors

Tension shading

Stress glow

Narrative blocks with personality

🧑‍🤖 3. Have character-driven agents

Agents appear:

recognizable

expressive

readable at a glance

with soft emotional signals

📚 4. Offer a Story Mode

A one-click full-episode view that:

scrolls like a comic

explains itself like a documentary

feels cohesive & enjoyable

🧩 5. Be ready for Era III without rework

Era II produces the visual and structural scaffolding for:

divergence overlays

interactive exploration

cognition maps

expansion of beats into animated sequences

the cinematic layer

🧪 6. Remain fully tested and stable

smoke-level tests for new components

snapshot guards for story mode

maintain existing VM-first approach

🎨 Founder-Specific Responsibilities (Summary)

You will be needed for:

1) Approving visual/mood directions at key checkpoints:

Phase 1 visual language

Phase 2 storyboard composition

Phase 3 avatar / identity style

Phase 4 story mode direction

Optional Phase 5 iconography

2) Reviewing mockups and giving quick yes/no approvals
   (Helios will minimize requests — 5–10 approvals total, each <5 min to review.)

3) Providing small creative phrasing if you want
   Episode summaries, taglines, tone preferences. Totally optional.

4) Generating any custom graphics if you want them (not required)
   Junie will produce everything procedurally unless you want custom flair.

⚠️ Reality Check from Helios (the candid version)

We cannot:

Turn Loopforge into 3D

Build Pixar-grade animations

Spend cycles on brand-new data structures

Expand VMs in ways that break backward contracts

Add heavy React frameworks

Build bespoke art assets for every agent

We can:

Make it visually expressive in 2D

Use CSS / SVG cleverly

Build storyboards and story mode

Add expressive identity cues

Add small tasteful animations

Build cognition overlays later in Era III

Keep everything lightweight and performant

Everything planned in Era II is absolutely achievable with this team size.