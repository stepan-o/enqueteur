# ARCHITECTURE_EVOLUTION_PLAN

## 🎬 Context — The Producer North Star

For full creative intent, see:

- `docs/PRODUCER_VISION.md`

The job of the architecture is **not** to make smarter robots.  
The job is to make their psychology **observable, narratable, and steerable** so that episodes are worth watching.

This document exists to answer one question for future architects:

> “Given that North Star, what parts of the system are stable, and what are the next few safe places to evolve it?”

---

## 1. Canonical Pipeline (Stable)

This seam is the spine of Loopforge and must **not** be broken:

Environment (truth)
 → AgentPerception (subjective slice)
 → Policy (stub or LLM)
 → AgentActionPlan
 → Legacy action dict
 → Environment (truth updated)
 → Below the seam: world truth (grid, positions, incidents, raw state).
 → Above the seam: perception shaping, traits, Supervisor bias, narratives, lenses, and log analysis.

All future changes must keep this structure:
* Decisions flow through Perception → Policy → Plan.
* The environment updates from plain, inspectable actions.
* Anything “psychological” lives above the seam, never inside world mechanics.

## 2. Current Architecture Snapshot (What’s Already Real)
### 2.1 Types & Traits
* `AgentPerception`, `AgentActionPlan`, `AgentReflection` live in `loopforge/types.py`.
* Traits (e.g. `guardrail_reliance`, `risk_aversion`, `obedience`, `satisfaction`, etc.) live in `loopforge/emotions.py` and round-trip via JSON.

Decision mode:
* `AgentActionPlan.mode` is `"guardrail"` or `"context"` (defaults to `"guardrail"`).

Perception mode:
* `AgentPerception.perception_mode`: `"accurate" | "partial" | "spin"` (configured via `PERCEPTION_MODE` in `loopforge/config.py`).

### 2.2 Logging & Days
Step-level logging (JSONL)
* `ActionLogEntry` + `JsonlActionLogger` record each decision:
* full `AgentPerception`,
* plan fields (intent, movement, targets, narrative, mode),
* `policy_name` (for future experiments),
* raw legacy action dict.

Day orchestration & reflections
* `loopforge/day_runner.py:`
  * `run_one_day(...)` runs N steps, aggregates logs, runs reflections.
  * `run_one_day_with_supervisor(...)` wraps the above with Supervisor messaging.
  * `run_episode(...)` orchestrates multi-day runs with (episode_index, day_index) tagging.
* `ReflectionLogEntry` + `JsonlReflectionLogger`:
  * store `AgentReflection` per day + metadata (agent, role, day, episode, perception mode, perceived supervisor intent).

Reflections & trait drift:
* `loopforge/reflection.py` implements:
  * `summarize_agent_day(...)`,
  * `build_agent_reflection(...)`,
  * `apply_reflection_to_traits(...)`.

Drift is **small and clamped**, opt-in via orchestrator config.

## 2.3 Supervisor & Bias
* `SupervisorMessage` (`loopforge/types.py`) captures guidance:
  * intent: "tighten_guardrails" | "encourage_context" | "neutral_update",
  * optional episode_index.
* `JsonlSupervisorLogger` logs one JSONL line per message.
Bias & perception:
`SupervisorIntentSnapshot` in `loopforge/types.py`.
* `loopforge/supervisor_bias.py`:
  * `infer_supervisor_intent(...)` uses traits (e.g. obedience, blame_external, risk_aversion) to derive how the robot feels about the Supervisor.
* `AgentPerception.supervisor_intent` carries that snapshot.
* Reflections capture `supervisor_perceived_intent` at day end.

## 2.4 Truth vs Belief Drift (Perception Modes)
* `loopforge/perception_shaping.py`:
  * `shape_perception(perception, env)`:
    * `"accurate"`: no-op.
    * `"partial"`: hides/truncates details.
    * `"spin"`: tone-shifts summaries using Supervisor context / world state.
  * Reflections are tagged with `perception_mode` for later analysis.

World truth always lives in the environment and logs below the seam.
Perception modes only change **what the robots think they see**, never the actual physics.

## 2.5 Metrics, Weave & Episodes
Metrics harness (`loopforge/metrics.py`):
* JSONL readers for actions, reflections, supervisor logs.
* Helpers such as:
  * `compute_incident_rate(...)`
  * `compute_mode_distribution(...)`
  * `compute_perception_mode_distribution(...)`
  * `compute_supervisor_intent_distribution(...)`
  * `compute_belief_vs_truth_drift(...)` (using perception modes as a proxy).
* Segmenters:
  * `segment_by_episode(...)`
  * `segment_by_day(...)`
Episode tension weave (`loopforge/weave.py`):
* `EpisodeTensionSnapshot` (`loopforge/types.py`) with:
  * counts (days, actions, reflections),
  * incident/belief/guardrail/context/punitive/supportive/apathetic rates,
  * tension_index ∈ [0,1],
  * short human notes.
* `compute_episode_tension_snapshot(...)` & `compute_all_episode_snapshots(...)`.
* `JsonlWeaveLogger` writes `EpisodeTensionSnapshot` JSONL.

### Episode-Level Psychological Layers (Deterministic, Read-Only)

Recent additions extend the episode analysis stack without touching simulation logic.

**Story Arc Engine (`EpisodeStoryArc`)**
- Maps tension trend + supervisor activity + emotional arcs into:
  - `arc_type`, `tension_pattern`, `supervisor_pattern`, `emotional_color`
  - 3–6 summary lines for CLI recaps
- Lives in: `loopforge/story_arc.py`

**Trait Drift (`trait_snapshot`)**
- Derives tiny (~0.02–0.05) clamped changes for:
  - resilience, caution, agency, trust_supervisor, variance
- Inputs: stress start→end, guardrail/context mix, attribution, story arc
- Appears in: `summary.agents[name].trait_snapshot`

**Long Memory (`AgentLongMemory`)**
- Aggregates identity-like metrics across episodes:
  - cumulative stress/incidents,
  - trust_supervisor, self_trust, stability, reactivity, agency
- Only appears in `EpisodeSummary.long_memory`
- No sim-loop side-effects.

These all live above the seam and are analysis-only.

Episodes:
* `ActionLogEntry`, `ReflectionLogEntry`, `SupervisorMessage` now include `episode_index` and `day_index` (optional).
* `run_episode(...)` tags days and loops without changing world truth semantics by default.

## 2.6 Narrative Stack & Daily Logs
Narrative viewer (`loopforge/narrative_viewer.py`):
* Builds `DayNarrative` from `DaySummary` / `AgentDayStats`:
  * intro line,
  * per-agent beats (intro, perception, actions, closing),
  * supervisor line,
  * day outro.
* Deterministic templates, tension-aware outros, role flavor, stress bands.

Episode recaps (`loopforge/episode_recaps.py`):
* `EpisodeRecap` with:
  * episode intro (tension trend),
  * per-agent blurbs (stress arc, guardrail reliance, vibes),
  * closing line based on final tension.

Recaps now integrate:
- Story Arc summary block (if present)
- Trait Drift snapshots
- MEMORY DRIFT block (when long-memory crosses thresholds)

Explainer (`loopforge/explainer_context.py`, `loopforge/explainer.py`):
* Builds structured contexts from telemetry.
* Generates **developer-facing explainers** per agent:
  * tension profile,
  * stress arc,
  * guardrail vs context usage,
  * alignment with global episode mood.

Daily logs (`loopforge/daily_logs.py`):
* `DailyLog` with:
  * trend-aware intro,
  * per-agent beats (role flavor, stress band, guardrail/context skew, deltas vs previous day),
  * general beats (supervisor presence, protocol vs context skew, stress drift),
  * closing line based on end-of-day tension.

Emotional Arc Engine (EA-1)
- Each agent receives a derived `AgentEmotionState { mood, certainty, energy }`
- Used by day narratives for intros/outros and closing tones.

Memory Drift (Episode Recap)
- When Long Memory is available, `view-episode --recap` appends a short
  **MEMORY DRIFT** block summarizing long-term identity shifts.

All of the above are **pure, deterministic, telemetry-only** layers wired into CLI via flags:
* `--narrative`
* `--recap`
* `--daily-log`
* `explain-episode`

These are the current foundations for the “show.”

## 2.7 LLM Lens Scaffolding
LLM-ready lens (`loopforge/llm_lens.py`):
* Dataclasses:
  * `LLMPerceptionLensInput`, `LLMPerceptionLensOutput`,
  * `LLMEpisodeLensInput`, `LLMEpisodeLensOutput`.
* Builders:
  * `build_llm_perception_lens_input(day_summary, agent_name)`
  * `build_llm_episode_lens_input(episode_summary, characters, episode_id="ep-0")`
* Deterministic “fake LLM” functions:
  * `fake_llm_perception_lens(...)`
  * `fake_llm_episode_lens(...)`

CLI:

`lens-agent` command shows lens input + fake output for one agent/day.

This layer defines the contract an actual LLM would later implement:
* Inputs: tension, stress, guardrail vs context, supervisor tone, role, etc.
* Outputs: emotional read, risk assessment, suggested focus, supervisor prompt.

No real LLM is wired yet; this is intentional.

Lens inputs now include emotion state, story arc hints, and attribution summaries so future policies can align emotional and narrative arcs.

## 3. Near-Term Evolution (What’s Allowed to Change Next)
To avoid a 13-phase forever-roadmap, evolution is scoped to a few **Producer-aligned bets.**

### 3.1 Policy Variants & Experiment Harness
Goal: make different policies **visibly change the show** (not just numbers).
* Introduce explicit `RobotPolicy` interface and registry.
* Implement at least:
  * guardrail-heavy policy,
  * context-heavy policy,
  * experimental/LLM-backed policy (when ready).
* Ensure `ActionLogEntry.policy_name` is consistently set.
* Add metrics helpers / simple CLI views to compare:
  * tension_index,
  * incident rate,
  * guardrail/context mix per policy.

Success criteria: switching policies results in clearly different **narratives**, not just metrics.

### 3.2 Human-Facing Log & Weave Viewer
Goal: make it trivial for a human to binge an episode.

* Lightweight viewers (CLI or HTML/TUI):
  * `view_actions`
  * `view_reflections`
  * `view_supervisor`
  * `view_weave` (episode tension timeline)
* Use existing logs + narrative/daily/recap layers; **no new core mechanics.**
* Focus on:
  * per-agent arcs,
  * mode and perception overlays,
  * episode tension curves.

Success criteria: a new contributor can understand “what happened this episode” without reading the code.

### 3.3 Incident DB & Scenarios (Optional, Later)
Goal: eventually ground tension & incidents in DB-backed world truth and reproducible scenarios.
* Introduce `IncidentRecord` model (DB or SQLite).
* Link incidents to action timestamps.
* Add scenario configs: seeds, starting conditions, constraints.

This is **explicitly lower priority** than:
* policy experiments, and
* human-facing viewers.

Do not build this first unless story needs it.

### 3.4 Episode Psychology Stabilization (Optional, Safe)

Goal: ensure narrative consistency across multiple episodes.

Scoped improvements:
- formalizing thresholds for emotion → story arc labels,
- defining drift caps per-season (to avoid runaway traits),
- optional viewer tools for long-memory timelines,
- richer attribution categories (no sim behavior changes).

All remain above the seam and purely presentational.

## 4. Working Rules for Future Architects
* Do not break the **Perception → Policy → Plan** seam.
* Do not mix world truth with agent belief.
* Do not add black-box behavior that can’t be explained via logs.
* Do not ship a change that makes the output less interpretable or less entertaining.
* All episode-level psychology (story arcs, traits, long memory, attribution) must remain deterministic, pure, and log-derived. Nothing in these layers can ever alter simulation behavior.

If in doubt, re-read:
* `docs/PRODUCER_VISION.md`

and then ask:

> “Does this change make the show easier to watch, explain, or play with?”

If the answer is no, don’t do it.