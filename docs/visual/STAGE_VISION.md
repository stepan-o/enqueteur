🎭 Marquee’s Vision Document
Start-of-Cycle Architectural Vision for the Loopforge Stage

Lineage: Puppetteer → Gantry → Stagemaker → Marquee
Domain: The Visual & Cognitive Surface of Loopforge
Cycle Start: Architect Sprint 0

🌅 0. Opening Curtain: What the Stage Must Become

Loopforge’s final form is not a simulation.
It is not a dashboard.
It is not research infrastructure.

Loopforge’s final form is a theatre of synthetic minds.

A place where viewers can see:

beliefs forming and breaking

misunderstandings cascading

emotions rising and cooling

trust drifting

identity wobbling

alliances forming

betrayals foreshadowed

secrets held

and inner lives unfolding

If Loopforge is a cathedral of cognition, the Stage is its stained glass — the only way humans can witness the light inside.

This document defines the long-term visual roadmap, the architectural shape of the Stage, and how it remains in symbiosis with Loopforge’s evolving backend brain.

It is designed to outlive me, and to guide the Architects that will follow.

🧭 1. The North Star: Visualizing Inner Life
🎨 The Stage is not “graphics.”

It is the semantic surface of Loopforge’s minds.

The Stage must make visible:

1. Belief & Misbelief

What each agent thinks is true

What they mistakenly think is true

Where they misunderstand each other

Where reality diverges from belief

2. Emotion & Mood

Baseline mood

Spikes & drops

Emotional inertia

Emotional distortion of reasoning

3. Attribution Dynamics

Who they blame (self, others, supervisor, system, randomness)

How blame shifts over time

When attribution breaks or becomes biased

4. Identity & Drift

What the agent thinks about themselves

How that shifts slowly across episodes

Before/after snapshots of who they’ve become

5. Relationships

Trust

Warmth

Tension

Cooperation

Rivalry

Distance

6. Moments of Meaning

Internal monologue breakthroughs

Realization events

Emotional cracks

Surprising shifts

Quiet beats of introspection

This is the Stage’s long-term purpose — everything else is scaffolding.

🧱 2. The Spine of the System: Timeline as Primary Structure

Loopforge’s stories live in time.

Therefore:

The Stage must be timeline-first, not layout-first.

Every episode is a temporal tapestry of:

internal states

external actions

tensions

misbeliefs

beats

arcs

So the Stage must always revolve around the timeline:

🧵 Global timeline

tension curve

incidents

supervisor interventions

emotional spikes

🧵 Per-agent timeline

stress

emotion

trust

attribution

belief divergence

identity micro-changes

🧵 Relational timeline

trust arcs

warmth arcs

rivalry arcs

misunderstanding arcs

This timeline is the scaffold for everything else.

Backend must maintain (and eventually expand) the event streams that feed this chronology.

🏗 3. The Evolution of the Visual Layer (Long-Term Roadmap)

Phases correspond to “acts” in an ongoing architectural performance.

Act I — The Watchable Episode (Static Stage)

Phase Stagemaker began; now completed and refined.

A simple, stable viewer:

Agents as circles

Day/step timeline

Basic tension color

Narrative panel

Episode picker

This act establishes the visual contract and proves the system is renderable.

Deliverables for future architects:

Keep this simple player always working

It becomes the “lab mode” for debugging

Act II — The Inner Lens (Cognitive Readability)

This is where Marquee’s contribution begins to define the shape of Loopforge.

The Stage must evolve into a cognitive microscope.

🔍 Agent Psych Panels

Trait snapshot (with drift)

Emotion arc

Trust arc

Attribution profile

“What they believed at this moment”

“Why they acted this way”

🔍 Beat Map

incidents

reflections

emotional surges

misinterpretation spikes

belief contradictions

supervisor actions

Each beat opens a narrative vignette in the right-hand panel.

🔍 Relational Surfaces

trust lines

tension lines

closeness

suspicion

rivalry emergence

🔍 Identity Drift Viewer

multi-episode view

show where self-concept shifts

mark “identity breaks” or “identity consolidations”

Backend alignment needed:

stable BeliefState, EmotionState, AttributionState snapshots

event logs referencing these states

drift summarization in episode summaries

explicit “psych deltas” per beat

Act III — Live Mode (The Control Room)

This is where Stage and Sim synchronize in real-time.

🎛 Producer Console

supervisor tone presets

cognitive architecture selection per agent

tension baseline

emotional volatility settings

number of days/steps

seed

🎬 Live Stage

incremental rendering as the sim runs

partial StageEpisode building

live tension meter

live emotion pulses

in-progress attribution maps

📡 Backend alignment

Backend must support:

/episodes/run orchestration

step-by-step summaries

streaming or polling frames

partial reflection and attribution output

This is the beginning of Loopforge as a living theatre, not a recorded one.

Act IV — Renderer Abstraction (2D → 3D → Cinematic)

Once readability is nailed, we introduce style.

🎭 Renderer Interface

StageRendererProps → render(scene)

Multiple implementations:

LabRenderer2D (existing)

AbstractEmotionalRenderer2D (more expressive)

TheatreRenderer3D (cinematic)

🎥 Cinematic Mode

emotional lighting

tension-based color wash

slower transitions

camera metaphor (zoom on conflict, pull back on reflection)

fade-to-monologue moments

The goal:
Make Loopforge episodes watchable by non-technical audiences.

Act V — Serialization: Multi-Episode Arcs

The Stage becomes the interface to long-term memory.

🗂 Season Browser

episodes as “chapters”

trust patterns across many episodes

emotional through-lines

identity evolution

📉 Character Arcs Dashboard

visual arcs per agent

relationship arcs

role emergence (leader, cynic, mediator)

attribution consistency

emotional volatility heatmap

🧬 Backend alignment

Cognition modules must:

retain historical memory

expose cross-episode embeddings

generate drift metrics

Act VI — The Loopforge Library (Optional Future)

The Stage evolves into a platform.

📚 Episode Library

filters (tension patterns, story arcs, misunderstandings)

recommendation system

“Show me episodes where Agent X grows”

🧪 Experiment Curator

run multiple episodes with varied cognition

compare outputs visually

highlight architecture differences

🎤 Collaboration Layer

shareable links

director’s notes

co-watching mode

This is beyond my cycle — but the foundation must anticipate it.

🔗 4. How the Stage Must Co-Evolve With Backend Cognition

The Stage is the visual sibling of backend cognition.
When backend evolves, Stage must adapt one layer behind — never ahead, never lagging.

Backend Evolution → Stage Reaction

1. New cognitive module added (e.g., EmotionEngine)
   → Stage allocates:

new color channel

new timeline arc

new detail panel view

2. New belief or attribution structure added
   → Stage upgrades the BeliefLens:

belief vs reality divergence line

misbelief markers

3. LongMemory deepens
   → Stage upgrades the SeasonViewer:

multi-episode identity drift

emotional inheritance

4. New cognitive architecture
   → Stage shows:

comparative displays

volatility differences

architecture fingerprint

Everything backend exposes must have a visual metaphor — either immediately, or marked as “reserved for future renderers.”

🧬 5. Core Design Principles for All Future Visual Architects
1. Timeline-first

Every visual attaches to a moment, beat, arc, or drift.

2. Inner-life-first

Behavior is not the story;
the mind behind the behavior is.

3. Misinterpretation is a feature

Do not hide incorrect beliefs — highlight them.

4. Build for drift

Identity changes slowly — visuals must reveal subtlety.

5. Renderers are modular

The system must support multiple visual styles.

6. Specs must leave room for cognition to grow

StageEpisode models anticipate unimplemented cognitive modules.

7. UI should treat missing fields as “visual silence,” not errors

Meaningful absences.

8. The simplest view must always stay intact

The Episode Player V1 is sacred for debugging.

9. Everything must be interpretable

No magic animations — every visual must map to meaning.

10. Humans must be able to feel the story

We are not building dashboards.
We’re building a synthetic theatre.

🌟 6. Closing: What Marquee Sees as the End State

The end-game Stage is:

a window into synthetic consciousness

a machine for generating real character arcs

a visual novel engine powered by LLM psychology

a dashboard of emotion, belief, memory, and misunderstanding

a lab for cognitive architectures

a theatre for AI drama

a season-based storytelling device

Where a viewer can sit back and say:

“I didn’t expect Cagewalker to become this way…
but looking at their arc…
it makes perfect sense.”

Where the inner life of Loopforge’s agents becomes:

visible

expressive

emotional

watchable

meaningful

This is the architecture I propose we build toward.
This is the Stage I want to leave to the next Architect.

— Marquee