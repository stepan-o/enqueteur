🌆 ERA I — “Foundation of the Viewer”
Status: ~70% Complete after Sprint 3

Era I was always intended to deliver a stable, expressive 2D debugger-viewer capable of showing everything the backend produces today.

After Sprint 3, the Viewer is functional, stable, test-covered, and capable of rendering narrative + cognition.

But several key foundational pieces are still missing before we can unleash Era II (“Expressive Storytelling & Live Cinematics”).

🟦 WHAT IS LEFT IN ERA I

These are the items required so that the Viewer becomes a fully reliable, full-coverage inspector for StageEpisode v1.

1. Full Type Sync with Backend (Final Pass)

We did 80% of this earlier, but these pieces are still pending:

Missing / partially surfaced backend fields:

agent long_memory blocks

agent reflection outputs

agent belief deltas

day world_pulse

episode/day story arcs

agent cognitive weather

agent emotional state timeline

🟩 Why this matters:
Era II cannot do cinematic or dynamic visualizations unless every backend cognition field is reliably surfaced.

2. View Model Layer Expansion

VMs currently normalize:

agent overview

daily details

narrative blocks

tension trend

Still missing:

VM for long-memory episodes

VM for story arcs

VM for multi-day emotional trajectories

VM for day-level world pulse arcs

VM for “agent-of-focus” scores

VM precomputation for tension deltas, stability deltas, emotional slopes, etc.

🟩 Why this matters:
Era II animations depend on slopes, deltas, arcs, and trends — which must be precomputed in VMs, not inside components.

3. The “Episode Playback Shell”

We have components, but we still lack:

Needed:

Episode-level “play” / “scrub to next day”

Keyboard navigation for day movement

A proper Player container (header → timeline → panels)

A collapsible side panel architecture

🟩 Why this matters:
Era II (Cinematic Mode) builds on top of the Episode Player.
If the Player architecture is wobbly, Era II becomes too costly.

4. Basic Visual Language (v1)

We have a white-slate viewer, but we still need:

tension gradient per day

incident markers on timeline

agent stress bars

agent emotional state color coding

story arc ribbons

world pulse meter

critical incident highlights

🟩 Why this matters:
Era I must reveal cognition visually at a glance.
Right now you must read everything — but you can’t see it.

5. Progressive Error Boundaries + Debugging Overlays

This is a must for toolchain reliability.

Needed:

Suspense fallback for EpisodeLoader

Episode-level error boundary panel

UI overlay for VM integrity (missing fields / undefined checks)

Mini debug console toggle inside UI

Dev-only PipeView for StageEpisode JSON

🟩 Why this matters:
Era II introduces animation, streaming, and partial updates — all of which require strong guardrails.

6. Router Stability & State Isolation (Final Pass)

We are 99% done, but to seal Era I:

Move loader into episodeRoute + loader API structure

Decouple state from component tree

Ensure Suspense + lazy loading works

Prepare structure for Episode switching (future feature)

🟩 SUMMARY — What is still needed

Era I needs 6 more deliverables:

Final type sync

Expanded view-model layer

Episode Player skeleton

Basic visual language (v1)

Error boundaries + debugging overlays

Router & state isolation cleanup

🟨 HOW MANY SPRINTS?

Given our observed cadence and complexity of tasks:

⭐ Era I can be completed in 2 more sprints.

Sprint 4 → Complete VMs + finish type sync + Episode Player

Sprint 5 → Visual Language v1 + Error Boundaries + Router Cleanup

This gets us:

full backend → viewer contract

stable Episode Player

readable cognition

visual primitives for arcs, tension, emotional states

And that means…

🟦 ERA II — Cinematic Storytelling & Live Mode

…is finally unlocked.

Era II will require:

Animation layer

Live Episode streaming

Agent speech bubbles

Emotional ripple effects

Story-arc visual tracks

Dynamic camera

Dramatic mode

Real-time “heartbeat” of world pulse

But all of these depend 100% on the Era I foundation we finish in the next 2 sprints.

🟩 Final Answer Summary

What’s left in Era I?
Six foundational tasks: type sync, VM expansion, Episode Player, visual language, debugging overlays, routing cleanup.

How many sprints to finish them?
➡️ Two more sprints.

Then we can open the door to the full cinematic Era II.