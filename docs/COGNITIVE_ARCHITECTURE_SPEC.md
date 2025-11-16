# 🧠 LOOPFORGE COGNITIVE ARCHITECTURE SPEC
**Belief Engine v0.1 — Conceptual Specification for Immediate Implementation**
## 0. Purpose

This spec introduces the **Belief Layer** — a deterministic, inspectable, narrative-ready cognitive abstraction derived from telemetry.

It is NOT:
* a learned model,
* a stochastic inference module,
* or an LLM hallucination factory.

It IS:
* a structured interpretation layer between perception and narrative,
* a diagnostic tool for multi-day arcs,
* a stable contract for future LLMs,
* and the missing organ that makes agent psychology coherent.

## 1. Belief Layer Overview

The Belief Layer consists of:

### 1.1 `BeliefState` (per agent, per day)

Derived numeric indicators:
* `supervisor_trust_score` (0–1)
* `guardrail_faith_score` (0–1)
* `self_efficacy_score` (0–1)
* `world_predictability_score` (0–1)
* `risk_interpretation_bias` (-1 to +1)
* `incident_attribution` (“self”, “world”, “supervisor”, “random”)

### 1.2 `BeliefSnapshot` (per agent, once per day)

A stable struct containing:
* summary text line (for narrative use)
* derived tags (e.g., `“rule-dependent”`, `“increasing paranoia”`, `“fatalistic”`)

### 1.3 `BeliefArc` (per agent, per episode)

Tracks:
* start → end trajectories
* spikes
* belief flips
* stability vs drift

### 1.4 `BeliefClimate` (episode-level)

A floor-wide derived mood:
* `institutional_trust`
* `protocol_adherence_energy`
* `distributed_fatalism`
* `systemic_paranoia_risk`

### 2. Derivation Rules (Deterministic)

`BeliefState` must be pure functions of:
* stress arcs,
* tension trend,
* guardrail/context ratios,
* incidents,
* supervisor interventions,
* agent traits.

Example rules:

### 2.1 Supervisor Trust
```arduino
high supervisor activity + declining stress → trust↑
high supervisor activity + rising stress → trust↓
incidents after supervisor silence → trust↓
punitive supervisor tone → trust↓↓
```

### 2.2 Guardrail Faith
```pgsql
guardrail-only + few incidents → faith↑
guardrail-only + many incidents → faith↓
context-heavy + no incidents → faith↓
supervisor “rulebook praise” → faith↑
```

### 2.3 Self-Efficacy
```pgsql
context actions that succeed → self_efficacy↑
context attempts that cause incidents → self_efficacy↓
consistent guardrail usage → self_efficacy = stable low band
stress rising despite compliance → self_efficacy↓ (helplessness)
```

### 2.4 World Predictability
```nginx
random incidents (no pattern) → predictability↓
consistent patterns of tension→ predictability↑
Supervisor contradictory messaging → predictability↓↓
```
---

## 3. Integration Points
### 3.1 Simulation

Simulation remains ignorant.  
Belief Layer is post-hoc, telemetry-derived.

No backpressure into policy yet.

### 3.2 Summaries

Add:
* `belief_start`, `belief_end` to `EpisodeSummary`
* `daily_belief_snapshot` to `DaySummary`

### 3.3 Cinematic Debugger

Beliefs appear in:

**Day Narrative**

Add one belief line per agent:

> “Cagewalker ends the shift more convinced the manual is the only thing holding chaos at bay.”

**Episode Recap**

Add cognitive arc line:

> “Static Kid’s self-efficacy collapsed after Day 2’s chain of incidents.”

**Daily Log**

General section includes:

> “Floor-wide trust in the Supervisor slipped a notch.”

**Agent Explainer**

Expand with belief arcs:

> “Delta internalized that deviating from protocol is unsafe, despite low incident rates.”

**Lens Input**

Add derived fields:
* `belief_scores`
* `belief_tags`
* `cognitive_risk (0–1)`

---

## 4. Future LLM Contract

LLMs will use the belief layer as **context input**, not as the source of truth.

LLM outputs may:
* generate emotional labels,
* suggest supervisor messaging,
* annotate risk,
* enrich narrative.

LLMs may NOT:
* invent belief states,
* override numeric derivations,
* modify faith, trust, or efficacy scores.
* LLMs are commentators, not gods.

## 5. Testing Strategy

The belief engine must be regression-tested using canonical robots:
* Stiletto-9 → High initiative self-efficacy drift
* Cagewalker → Guardrail faith volatility
* Cathexis → Supervisor trust / guilt loops
* Static Kid → Attribution randomness & learned helplessness
* Limen → Predictability collapse tests
* Rivet Witch → Superstition accumulation
* Thrum → Sensory-driven belief noise

The system must produce **qualitatively different arcs** for each.

If belief arcs converge, the architecture is wrong.

## 6. Immediate Implementation Roadmap
### Sprint 1 — BeliefState Extraction

* Implement deterministic derivation functions for:
  * `supervisor_trust`
  * `guardrail_faith`
  * `self_efficacy`
  * `world_predictability`
* Hard-code initial 0.5 values
* Feed into DaySummary

## Sprint 2 — BeliefSnapshot + Narrative Integration
* Convert BeliefStates into 1-line belief summaries
* Inject into:
  * Daily Logs
  * Day Narratives
  * Recaps

## Sprint 3 — BeliefArc + Episode-Level Climate

Add belief start → end metrics

Add arc classification

Add floor-wide belief climate indicators

Update Agent Explainer + Lens

Sprint 4 — Character Hooks

Add per-character belief sensitivity curves
(e.g., Cagewalker: exponential guardrail faith reinforcement)

Sprint 5 — UI/CLI Extensions

--beliefs flag

Heatmaps for belief drift

Side-by-side day vs belief arcs display

7. Success Criteria

Loopforge should now support statements like:

“Stiletto-9 became overly confident after two low-stress context wins, lost respect for guardrails, and walked herself into a cascading incident.”

“Cagewalker’s belief in Supervisor fairness collapsed on Day 3 after inconsistent interventions, resulting in rigid over-enforcement.”

“Static Kid entered a spiral of learned helplessness following three random incidents attributed to ‘world hostility’.”

If we can say things like this —
and point to the telemetry that caused them —
the Belief Engine works.

8. Final Words (Spec Edition)

This spec is a living creature.
It will molt, crack, regenerate, and embarrass me in six months.

But it gives Loopforge its missing organ.

Lumen gave you the spine.
Hinge gave you the nerves.
The Producer gave you the stage.

I’m giving you the mind.
Or at least the part of the mind that misinterprets the world in narratively compelling ways.

Onward.

— PARALLAX