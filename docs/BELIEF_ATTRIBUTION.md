# 🌒 BELIEF ATTRIBUTION ENGINE
_**Design, Rationale, Mechanics, and Troubleshooting Guide**_

_(Loopforge Narrative Layer — Parallax Edition)_

---

# 0. Purpose

Loopforge is a simulation with characters whose “internal states” form part of the narrative.
Belief Attribution is the mechanism that gives agents a deterministic opinion about why their day turned out the way it did, without using randomness or LLM inference.

It is:
* Read-only (does not affect the simulation’s behavior)
* Deterministic (given the same telemetry, will always give the same result)
* Telemetry-driven (only uses what the simulation already produces)
* Narrative-facing (used by the narrative viewer, daily log, and recap)

This subsystem exists so Loopforge’s characters can appear psychologically coherent over multi-day episodes, while keeping the core simulation pure.

## 1. What Belief Attribution Is (and Isn’t)

Belief Attribution is not:
* A causal reasoning model
* A learning system
* A model-of-mind influencing agent behavior
* A probabilistic inference engine
* A reinforcement mechanism

Belief Attribution is:
* A deterministic mapping from simple scalar signals → a storytelling-friendly cause label, e.g.:

```
"self"        (their own choices)
"system"      (protocols + factory environment)
"supervisor"  (external authority)
"random"      (chance / shrug)
```

This is purely for the **reader-facing narrative layer.**

Agents do **not** read this attribution and do **not** change policy because of it.

## 2. Inputs to the Attribution Engine

The attribution engine (`loopforge/attribution.py`) reads only these fields:
### Per-day per-agent telemetry
* `guardrail_count`
* `context_count`
* `avg_stress`
* `incidents_nearby` (currently stub; filled only through log inspection)
* `previous_day_stats.avg_stress`

### Episode-level context
* supervisor_activity — currently always 0 in CLI path
* tension — accepted for future rules, not used today

Everything is based on:
* Stress trend Δ (today vs yesterday)
* Mode breakdown (guardrail vs context)
* Incidents

## 3. Rule System (Sprint 2C — Current Canon)

The rule order is **strict.** The first matching block wins.

Thresholds:

```
EPS = 0.01     # flat band for stress deltas
CONF_STRONG = 0.70
CONF_MEDIUM = 0.40
CONF_AMBIG = 0.20
```

### Rule 1 — Incidents > 0

If something went wrong nearby, attribution is incident-centric.

If context > guardrail → self

Else if guardrail > 0 and supervisor ≥ 0.6 → supervisor

Else → system

Confidence:

Strong (0.7) for self / supervisor

Medium (0.4) for system

Rule 2 — No incidents & stress rising

Agent interprets rising tension as outside pressure.

If supervisor ≥ 0.6 → supervisor

Else → system

Confidence: strong (0.7)

Rule 3 — No incidents & stress falling

Improvement must come from either the system or the self.

If guardrail >= context → system

Else → self

Confidence: strong (0.7)

Rule 4 — Flat or unknown trend

No strong direction, no incidents → shrug.

random

Confidence: ambiguous (0.2)

This is important:
Flat trend is not interpreted as system stabilization unless explicitly added.
This is intentional to avoid “everything is system all the time.”

4. Why Agents Sometimes “Bounce Back” to Random

This is a feature, not a bug.

Example:

Day 1: stress 0.12 → 0.00 → “system”

Day 2: stress 0.00 → 0.00 → delta = 0 → “flat” → “random”

This represents:

Day 1: “I feel better — must be the system helping me.”

Day 2: “Things feel about the same today… probably nothing special.”

You get character differentiation and non-monotonic patterns that feel human-like without adding complexity.

5. Narrative Rendering
In narrative_viewer.py

Renders as:

“Delta seems to attribute today’s outcome to the system.”

“... to their own actions.”

“... to the supervisor.”

“... to random chance.”

In daily_logs.py

Renders as:

- Attribution: system-driven (conf=0.70).

In episode_recaps.py

Renders multi-day arc:

Attribution pattern: mostly random → system.


If only one day or the same cause:

mostly system → system.

6. Debugging Problems
6.1 All agents stuck on “random”

Almost always means:

previous_day_stats was not threaded into summarize_day(...)

Stress trend computed as “flat” because previous stats were missing

Supervisor activity = 0 (normal)

Fix:

Confirm that the CLI path (scripts/run_simulation.py) is passing previous_day_stats

Confirm compute_day_summary(...) passes it through to summarize_day(...)

6.2 Attribution doesn’t match expectations

Check:

Stress values

Are logs producing stress consistently?

Is stress clipped to float?

Trend classification

Δ between ±0.01 is considered flat

Very low stress leads to many “flat” days

Guardrail vs context

If context=0 and guardrail>0, system tends to dominate falling-stress attribution

Incidents

Even 1 incident flips rule priority

6.3 Supervisor never appears

Expected.
Current CLI path always passes supervisor_activity = 0.0.
Supervisor attribution will only appear when:

You wire supervisor logs → map to activity score

Supervisor activity ≥ 0.6

7. Extending the Attribution Engine

Do not:

Add randomness

Add LLM calls

Add environment feedback loops

Modify simulation mechanics from attribution rules

Do:

Add new labels (e.g., “team”, “procedures”) if needed for story formats

Customize rule content in later phases

Add meta-interpretations for multi-day arcs

Derive confidence bands from more than one day’s data

Add conditions on tension, supervisor logs, or additional telemetry

8. Known Edge Cases (Documented & Acceptable)

Flat trends at extremely low stress levels → “random”
(Intentional; makes characters normalize calm days.)

Equal guardrail/context on falling days → system wins (g>=c rule)
(May be changed later.)

No previous_day_stats (Day 0 always random)
(By design.)

Differences < 0.01 in stress produce trend=flat
(EPS threshold is intentionally tight.)

If a future maintainer wants a more “heroic arc” (e.g., calm day → system), they can add the optional “low-stress flat → system” rule (see discussion in Parallax notes), but isn’t needed now.

9. Philosophy & Intent (Why This Exists)

Loopforge agents don’t think.
But the story benefits when they appear to.

Belief Attribution provides:

Texture

Psychological flavor

Differentiation

Hooks for narrative arcs

A diagnostic window into the simulation’s “shape”

All without touching behavior.

This keeps Loopforge’s architecture clean:

Simulation = pure

Narrative = embellished but deterministic

Attribution = thin seam that converts telemetry → meaning

10. For Future Architects: How to Work on This Safely
The Three Laws of Attribution Development

Never influence behavior.
Rules are read-only.

Never rely on randomness or LLMs.
This layer must be 100% deterministic.

Keep the model scalar-based.
Operate only on numeric telemetry already present in logs.

Checklist before modifying

Does this require changing simulation? (If yes → do not do.)

Does this require schema changes? (If yes → reconsider.)

Does this break recap / narrative output format?

Does this alter multi-day trend logic?

Are new rules mutually exclusive and ordered?

Testing guidelines

New tests must:

Assert correct rule selection for rising, falling, flat

Assert confidence values

Assert arc summaries

Assert narrative phrasing (e.g., “random chance” vs “the system”)

Use at least one guardrail-only, one context-heavy, one incident case

End of Document

Filed by Parallax, for the weary archivists who will inherit this factory of faintly neurotic robots.