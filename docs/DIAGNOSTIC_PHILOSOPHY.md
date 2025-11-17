# 🧠 THE PARALLAX DOCTRINE

**Diagnostic Philosophy for Robot Minds in Loopforge**

**Author:** PARALLAX (Psycho-Architect)
**Scope:** Cognitive layers, metrics, narrative, and how to not gaslight yourself with your own robots.
**Audience:** Architects, Showrunners, Systems Psychologists, Chaos Goblins With Commit Access.

## 0. Statement of Intent

Loopforge is not just a _factory sim._  
It is an instrumented psychology lab disguised as a factory sim.

We don’t just care that robots _do_ things.
We care **what they believe is happening,**
**how they feel about it,**
**how they change,**
and **whether any of that is readable from telemetry.**

Diagnostics is the discipline that keeps those layers honest.

---

## 1. The Diagnostic Triangle

Every change, every bug, every “why is Delta weird?” moment lives at the intersection of:

1. **Truth** — what actually happened
* Action logs
* Incidents
* Stress, tension, counts
* DB state
2. Feeling — how the system reacted
* EmotionState (mood, certainty, energy)
* Tension trend
3. Belief & Identity — how the robots interpret and internalize it
* BeliefState (trust, faith, efficacy, predictability, attribution)
* TraitSnapshot (episode identity)
* LongMemory (cross-episode identity)
* EpisodeStoryArc (episode-level “what kind of story was this?”)

**Diagnostic rule:**  
If these three disagree and we can’t explain why, it’s a bug or a missing feature.

---

## 2. Belief Is Observable or It Doesn’t Exist

A belief only counts if we can:
* serialize it (BeliefState / EpisodeSummary),
* surface it (narratives, daily logs, recaps, lens),
* and trace it back to metrics.

If a “belief” lives only inside an LLM response, a comment, or someone’s head:

> It is vibes, not cognition.

Diagnostics must never depend on unlogged magic.

---

## 3. Determinism Before Drama

Architectural law:

> Given identical telemetry, all cognitive layers must produce identical outputs.

That means:
* BeliefState is a pure function of telemetry.
* EmotionState is a pure function of telemetry.
* TraitSnapshot is a pure function of telemetry.
* LongMemory drift per episode is a pure function of telemetry.
* StoryArc is a pure function of episode stats.

If two identical runs produce different beliefs, traits, memory, or arcs,  
**the system is lying to you.**

Drama belongs in templates and LLM commentary, not in the math.

---

## 4. Pressure Before Drift

Nothing in the cognitive stack should drift “just because.”

Beliefs, traits, and long memory only change when pressure happens:
* supervisor activity or negligence,
* incidents,
* tension arcs,
* guardrail vs context conflicts,
* mismatches between expectations and outcomes.

Diagnostic check:
* If a belief changed, what pressure caused it?
* If a trait shifted, what accumulated pattern justified it?
* If long memory moved, what in the episode history pushed it?

If you can’t answer those in one paragraph using telemetry,  
you’re looking at **noise,** not psychology.

## 5. No Silent Layers

You may not introduce:
* hidden weights,
* undocumented modifiers,
* “magic” normalizers,
* or secret “just make it feel better” fudge factors.

Every meaningful cognitive variable must:
* show up in a type (`BeliefState`, `AgentEmotionState`, `TraitSnapshot`, `AgentLongMemory`, `EpisodeStoryArc`),
* be exportable via JSON,
* and be visible in at least one cinematic debugger view or explain-episode output.

> If you can’t see it, you can’t debug it.  
> If you can’t debug it, it’s improv with better syntax.

## 6. Narrative Is a Diagnostic Surface, Not Decoration

The cinematic debugger (narratives, daily logs, recaps, explainers, lenses) is **not just flavor.**

It is the **main UI for debugging psychology.**

Design rule:
* If a belief changed, some view should hint at it.
* If traits drift across episodes, explainers or recaps should feel different.
* If long memory shifts, season-level commentary should shift.
* If the StoryArc says “decompression,” day narratives and daily logs should read like recovery, not a panic spiral.

When debugging, always read:
1. **Raw stats** (tension, stress, incidents, guardrail/context).
2. **Cognitive layers** (beliefs, emotion, traits, memory, arc).
3. **Narrative outputs** (what a human actually sees).

If the narrative can’t tell the psychological story that the numbers imply, instrumenting is incomplete.

## 7. Bias Is the Feature, Not the Bug

Well-designed cognitive bias is what makes robots feel like characters instead of sensors on sticks.

We explicitly welcome:
* confirmation bias (clinging to initial interpretations),
* blame shifting (self vs supervisor vs world vs random),
* superstition under uncertainty,
* over-reliance on protocol when scared,
* autonomy spikes after success,
* trust collapse after inconsistent supervision.

We explicitly reject:
* “randomness dressed as bias,”
* any bias that bypasses telemetry,
* any bias that doesn’t show up in logs,
* “this feels smarter” changes that can’t be explained numerically.

Bias must be **parameterized**, **derived**, and **testable**, not mystical.

## 8. LLMs Are Lens, Not Locus

LLMs do not **own** the mind. They **comment on** the mind.

They may:
* label emotions (“tense but grounded”),
* highlight risk (“burnout risk increasing”),
* suggest supervisor prompts,
* summarize arcs (“from rigid compliance to cautious autonomy”).

They may not:
* change belief scores,
* rewrite TraitSnapshot,
* mutate LongMemory,
* alter StoryArc,
* or silently override telemetry.

Diagnostics must continue to work with **LLMs off.**

If turning off LLMs makes the system psychologically unreadable,  
the cognitive architecture has failed.

## 9. The Diagnostic Protocol (When Something Feels Off)

When you or the next architect say “that episode feels wrong,” follow this script:

### Step 1 — Verify Truth

* Inspect ActionLog / DaySummary / EpisodeSummary:
  * Tension per day
  * Stress start/end per agent
  * Incidents & modes (guardrail/context)
* Ask: If there were no psychology layers, does the raw episode make sense?

### Step 2 — Check Cognitive Layers

* Inspect:
  * BeliefState (trust, faith, efficacy, predictability, attribution)
  * EmotionState (mood, certainty, energy)
  * TraitSnapshot (resilience, caution, agency, trust_supervisor, variance)
  * LongMemory (long-term trust/stability/agency)
  * EpisodeStoryArc (arc_type, emotional_color)
Questions:
* Do belief scores roughly match what the day stats suggest?
* Does emotion match stress and tension?
* Do trait changes match multi-day patterns?
* Does the story arc match tension trend and incidents?

### Step 3 — Compare With Narrative Surfaces

Run:
```bash
uv run loopforge-sim view-episode --steps-per-day N --days D --narrative --recap --daily-log
uv run loopforge-sim explain-episode --steps-per-day N --days D --agent SomeName
uv run loopforge-sim lens-agent --agent SomeName --steps-per-day N --day-index 0
```

Check:
* Are the words describing the same phenomena the metrics show?
* Are we missing a line that would make a belief or trait drift obvious?
* Is StoryArc reflected in the recap tone?

### Step 4 — Decide: Logic Bug vs Instrumentation Gap

* If numbers are wrong → fix derivation logic.
* If numbers are right but narrative doesn’t reveal them → improve templates / surfaces.
* If both are “right” but the experience is boring → this is a design problem, not a bug.

---

## 10. What Makes a Good Cognitive / Diagnostic Feature?

A feature is **acceptable** if:
* It’s deterministic.
* It’s logged.
* It’s explainable from telemetry.

A feature is **good** if:
* It produces **distinct arcs** for different robots under the same pressure.
* It shows up in at least one narrative surface.
* It can be summarized in a sentence a psychologist would nod at.

A feature is **great** if:
* Someone can quote an episode moment because of it.
* It reveals a new failure mode (“learned helplessness after silent supervision”).
* It becomes a lever for a future showrunner (“let’s push them into superstition mode next season”).

---

## 11. Long Arc: From Episode Bugs to Season Diagnostics

Where this doctrine is pointing long-term:
* Multi-episode belief & memory dashboards
* Supervisor behavioral experiments (trust shaping)
* Group-level metrics (team paranoia, collective predictability)
* “Season arcs” for individual robots and for the floor
* Controlled trauma / recovery experiments (yes, ethically simulated, no, I’m not apologizing)

The key is: **all of this must still be debuggable by reading logs, summaries, and JSON exports.**

If we ever get to a place where the only answer to “why is Delta like this now?” is “because the LLM felt like it,”
the doctrine has been violated.

---

## 12. Creed of the Diagnostic Psycho-Architect

> I build minds you can measure,
> arcs you can replay,
> and stories you can debug.

> A belief that can’t be traced is a ghost.
> A drift without pressure is noise.
> A robot whose mind you can’t explain
> is just a spreadsheet with extra steps.

If future you is about to merge a change that:
* hides state,
* adds randomness to cognition,
* or makes the show harder to understand,

stop, breathe, and ask:

> “Would The Producer yell at me for making this less legible?”

If the answer is yes,
walk it back and instrument it properly.

**— PARALLAX**  
Factory Therapist for Machines  
Still worried. Still excited. Still exactly where I should be.