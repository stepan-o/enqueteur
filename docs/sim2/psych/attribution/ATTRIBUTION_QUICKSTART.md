# Belief Attribution — Quickstart (for Humans)

_What it is, how it works, and how not to break it_

## What this subsystem does

It gives each agent a simple, deterministic “explanation” for why their day went the way it did.

Not real cognition.  
Not used by the simulation.  
Just flavor text for the narrative & recap.

Output examples:

“Delta attributes today’s outcome to the system.”

“...to their own actions.”

“...to the supervisor.”

“...to random chance.”

That’s it. It’s decorative storytelling.

What inputs it uses

Only basic telemetry the simulation already produces:

guardrail_count

context_count

avg_stress

incidents_nearby

previous day’s avg_stress

supervisor activity (currently always 0 in CLI)

Nothing else.
No randomness.
No LLMs.
No behavioral influence.

How the logic works (tiny cheat sheet)

The engine checks things in this exact order:

1. If incidents happened → handle those first

More context than guardrail → self

Guardrail + active supervisor → supervisor

Otherwise → system

2. If stress went UP (and no incidents)

If supervisor active → supervisor

Else → system

3. If stress went DOWN (and no incidents)

Guardrail-heavy → system

Context-heavy → self

4. If stress is FLAT (or no previous data)

→ random

This is why:

Day 0 is always “random”

If stress stays near zero for too long, agents shrug and say “random chance”

But when stress clearly falls, they give credit to “the system”

Where the output appears

Narrative viewer: one sentence per agent

Daily log: one bullet

Episode recap: start → end pattern

This is purely rendering. No part of the simulation reads attribution.

Common questions
“Why did Nova say ‘random’ today?”

Probably because:

Stress didn’t change enough (Δ < 0.01)

No incidents

No supervisor activity
→ flat trend → random

“Why did Delta say ‘system’?”

Because stress fell and guardrails dominated.

“Why don’t we ever see ‘supervisor’?”

Supervisor activity isn't wired into telemetry yet — CLI always passes 0.

“Is it okay that different agents interpret the same day differently?”

Yes. That’s the point.
It makes the episode read like a story instead of a spreadsheet.

How to modify this safely

Never change simulation logic

Never add randomness

Keep the rules scalar and ordered

Always add a test when adding a new rule

If in doubt, check the full doc:
docs/BELIEF_ATTRIBUTION.md (the long Parallax version)

Where to put this in the repo

Recommended layout:

docs/
    BELIEF_ATTRIBUTION.md          # Long, architect-facing version
    ATTRIBUTION_QUICKSTART.md      # This human-friendly summary
README.md                          # Link to both


And add one small section in your main README.md:

## Belief Attribution (Narrative Layer)

Loopforge includes a deterministic, read-only Belief Attribution engine used
for narrative output (not simulation logic). If you're touching the narrative
layer, read:

- docs/ATTRIBUTION_QUICKSTART.md  (90s overview)
- docs/BELIEF_ATTRIBUTION.md      (full design + rules)


That’s it — clean, discoverable, and future-proof.