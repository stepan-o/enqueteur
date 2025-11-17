# 🛰️ Supervisor Activity — Deterministic Daily Scalar

**(Stable Cognitive Input, Read-Only, Telemetry-Driven)**

**Status:** Implemented, validated, integrated into narratives, arcs, and cognition layers.  
**Owner:** PARALLAX (but this one is boring, so mostly Junie)

## 0. What Supervisor Activity Is

**A pure telemetry scalar** in **[0,1]** representing how frequently the Supervisor acted _that day._
It is:
* **Deterministic**
* **Read-only**
* **Derived from logs only**
* **Never influences simulation mechanics**

It feeds cognition + narrative layers above the seam.

It is not:
* A behavior modifier
* A trust system
* A bias injector
* A stochastic value

It is simply “how present the Supervisor felt today.”

---

## 1. Formal Definition
```
supervisor_activity = (# of supervisor JSONL entries for the day) / steps_per_day
```

Clamped to `[0.0, 1.0].`

Edge case:

```
steps_per_day <= 0 → supervisor_activity = 0.0
```

This makes Supervisor Activity a **normalized presence signal.**

## 2. Where It Lives in the Pipeline

Scroll with me:

### 2.1 JSONL Loading (CLI Layer)

`scripts/run_simulation.py:`

* If a supervisor log exists, it:
  * Loads lines
  * Groups them by day_index
  * Computes supervisor_activity for each day
  (fallback: step // steps_per_day grouping)
  * Passes the scalar into compute_day_summary(...)

If no supervisor log:
* Activity defaults to `0.0`.
* This preserves old runs exactly.

### 2.2 Day Summary Construction

`loopforge/day_runner.py:compute_day_summary(...)`

Signature includes:
```
def compute_day_summary(..., *, supervisor_activity: float = 0.0)
```

* Value is inserted directly into the DaySummary dataclass.
* No inference. No rescaling. No embellishment.

### 2.3 Reporting Layer

`loopforge/reporting.py:summarize_day(...)`

* Simply forwards the scalar into the higher layers:
  * Emotion overlays
  * Story Arc heuristics
  * Episode-level trend builders

The reporting layer **does not reinterpret** the number.  
It just carries it upward.

## 3. Where It Is Used Today

Supervisor Activity is consumed in a **light-touch, deterministic** way by:

### 3.1 Story Arc Engine

(`loopforge/story_arc.py`)

* Helps classify supervisor pattern:
  * `hands_off`
  * `inconsistent`
  * `active_supportive`
  * `active_punitive`

It does not determine emotional color or arc type on its own — it is just one of several signals.

### 3.2 Emotion & Narrative Overlays

(`loopforge/narrative_viewer.py`, `daily_logs.py`)

* Day narratives mention supervisor tone only if activity crosses simple thresholds:
  * “stayed mostly quiet” → activity < 0.2
  * “kept a steady watch” → 0.2–0.6
  * “intervened often” → > 0.6

### 3.3 Episode Recap

(`episode_recaps.py`)

* Recap may include a supervisor-pattern line based on episode-level activity distribution.

### 3.4 Long Memory (Episode-Level Identity)

(`loopforge/long_memory.py`)

* Supervisor activity influences:
* trust_supervisor
* stability vs reactivity
* agency drift (slight, clamped)

It remains **one small contributor**, never the sole driver.

### 3.5 Trait Drift (Within-Episode Identity)

(`loopforge/trait_drift.py`)

* Used as a directional nudge:
  * Consistently high supervisor presence → slight increase in trust_supervisor trait
  * Consistently low presence → slight decrease

Effects are:
* deterministic
* clamped
* extremely small (≤ 0.02 per episode)

### 3.6 Lens Inputs (LLM Contracts)

(`loopforge/llm_lens.py`)

Included in both perception-lens & episode-lens inputs as a raw number:

```
supervisor_tone_hint
```

Fake LLM outputs reflect this but never modify values.

---

## 4. What It Does Not Do

To prevent future confusion:

Supervisor Activity **does not:**
* Modify stress
* Change tension
* Bias the simulation
* Rewrite perceptions
* Influence action mode
* Change incidents
* Create randomness
* Affect world truth

It is strictly **analysis-side metadata,** like humidity in a weather report.

---

## 5. Determinism & Safety Constraints

* No randomness
* No LLM calls
* No side effects
* No schema-breaking changes
* Telemetry-only input
* Pure function from logs

This scalar is safe, predictable, stable, and regression-tested.

## 6. Tests
### Unit

`tests/test_supervisor_activity.py`

Covers:
* 0 entries
* half entries
* overflows (clamp)
* zero steps (safe default)

### Integration

`tests/test_supervisor_activity_wiring.py`

Validates:
* correct per-day grouping
* scalar flows into DaySummary
* scalar appears in recap / narrative context where applicable
* EmotionState and StoryArc remain deterministic with this input

## 7. Design Philosophy Summary

Supervisor Activity is the **heartbeat monitor** for the supervisory layer:
* Low → “hands off”
* Mid → “present but light”
* High → “intervening consistently”

It is not a personality.
It is not a mood.
It is not a decision.

It is a **daily presence signal,** meant to feed:
* story arcs,
* emotion overlays,
* long-term identity drift,
* narrative consistency,
* future LLM interpretation tasks.

Readable. Deterministic. Psychological scaffolding.