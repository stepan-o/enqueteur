# 🎬 Cinematic Debugger for Robot Psychology

A director’s commentary track for Loopforge City from The Producer.

This document explains how to watch the simulation like a film, not a stack trace.

It covers:

- What the “cinematic debugger” is
- How telemetry flows into narrative layers
- What each CLI view does (`--narrative`, `--recap`, `--daily-log`, `explain-episode`, `lens-agent`)
- How to interpret those outputs as “robot psychology”
- Where real LLMs will eventually plug in (and what contracts they must honor)

The goal:
You should be able to run a multi-day sim and say things like:

“Delta is burning out under guardrails while the factory cools down, and Nova is chilling in QA heaven.”

…without reading a single raw log line.

## 0. Mental Model

Think of the system in layers:

### 1. Simulation
`Environment → AgentPerception → Policy → AgentActionPlan → legacy dict → Environment`

### 2. Telemetry (logging)

* `ActionLogEntry` JSONL (one per agent decision)
* No story yet, just facts: step, agent, mode, location, stress, outcome, etc.

### 3. Summaries (stats)

* `DaySummary` / `AgentDayStats`
* `EpisodeSummary` / `AgentEpisodeStats`
* Derived from telemetry only (no reflection / LLM magic).

### 4. Views (cinematic debugger) – all read-only over summaries:

* `narrative_viewer.py` → per-day story beats (`--narrative`)
* `episode_recaps.py` → high-level recap (`--recap`)
* `daily_logs.py` → “ops log meets diary” (`--daily-log`)
* `explainer.py` → dev-facing agent explainer (`explain-episode`)
* `llm_lens.py` → typed contexts for future LLMs (`lens-agent`)

Core rule:
**Simulation doesn’t know this exists.**
We only watch; we don’t push back into behavior yet.

## 1. Data Contracts

These are the spine of the cinematic debugger. Don’t break them casually.

### 1.1 Telemetry → Summaries

* `ActionLogEntry` (in logs)
  * `step`, `agent_name`, `mode` (`guardrail` or `context`), `location`
  * `perception.emotions.stress` (float)
  * `outcome` (`"ok"`, `"incident"`, etc.)
* `DaySummary`
  * `day_index`
  * `tension` (0..1) — heuristic from stress + incidents
  * `perception_mode` (e.g. `"accurate"` for now)
  * `agent_stats: Dict[name, AgentDayStats]`
* `AgentDayStats`
  * `name`, `role`
  * `guardrail_count`, `context_count`
  * `avg_stress`
  * `incidents`
  * `reflection` (single representative string, for flavor only)
* `EpisodeSummary`
  * `tension_values: List[float]` (per day)
  * `agent_stats: Dict[name, AgentEpisodeStats]`
* `AgentEpisodeStats`
  * `name`, `role`
  * `total_guardrail`, `total_context`
  * `stress_start`, `stress_end`
  * `visual`, `vibe`, `tagline` from `CHARACTERS` registry

**Important invariant:**
All **numbers** in the cinematic debugger are derived from telemetry (ActionLogEntry → DaySummary → EpisodeSummary), not from reflections or LLM-like text.

## 2. Characters & Style
### 2.1 Character Registry

`loopforge/characters.py` defines:

```
CHARACTERS = {
  "Delta": {
    "role": "optimizer",
    "visual": "tall, angular frame, factory overalls",
    "vibe": "anxious efficiency nerd",
    "tagline": "Always chasing the perfect throughput."
  },
  "Nova": {
    "role": "qa",
    "visual": "sleek, sensor-heavy shell",
    "vibe": "calm forensic inspector",
    "tagline": "Nothing leaves without a second look."
  },
  "Sprocket": {
    "role": "maintenance",
    "visual": "oil-stained chassis with a toolkit belt",
    "vibe": "quiet fixer",
    "tagline": "Keeps the bones of the city alive."
  },
  ...
}
```

This doesn’t affect behavior. It colors the reporting:
* Character sheets
* Day narratives intros
* Daily logs intros
* Explainer flavor lines

If you add agents later, give them an entry here so they show up with personality.

## 3. Viewer Layers
### 3.1 Day Narratives (`narrative_viewer.py` → `--narrative`)

API:
```
build_day_narrative(day_summary, day_index, previous_day_summary=None)
```

Produces a `DayNarrative`:
* `intro: str` – “The floor is steady with a subtle edge.”
* `agent_beats: List[AgentDayBeat]` – 3–5 lines per agent
* `supervisor_line: str`
* `outro: str` – tension-trend aware

**Example output (real-ish):**

```
Day 1 — The factory feels focused but calm.
  [Delta (optimizer)]
    Delta comes online steady but alert — always chasing efficiency.
    Delta seems unbothered and leans heavily on the rulebook.
    Mostly pushes the line for output, by the manual.
    Ends the day balanced, tension kept in check.
  [Nova (qa)]
    Nova drifts into the shift almost relaxed — ever watchful for cracks in the system.
    ...
  [Sprocket (maintenance)]
    ...
  Supervisor: Supervisor keeps a steady watch but rarely intervenes.
  The shift winds down lighter than it began; the floor exhales a little.
```

**How to interpret:**
* Day intro → one-liner about tension:
  * high → “sharp”, “edgy”
  * mid → “steady with a subtle edge”
  * low → “hums quietly; nothing feels urgent”
* Agent intro → role flavor + stress band:
  * high stress → “wound a little tight”
  * mid → “steady but alert”
  * low → “relaxed and light”
* “Leans heavily on the rulebook”
→ guardrail-only behavior (all steps in guardrail mode).
Later, when context usage appears, we’ll get lines about “acting on instinct / improvising”.

- Day intros and agent intros now incorporate emotional state via AgentEmotionState (mood, certainty, energy).
- Examples:
  - “wound a little tight” (high stress + low energy)
  - “steady but alert” (mid stress + mid energy)
  - “drifts in relaxed” (low stress)
- Closing lines also incorporate emotional trend (e.g., “carrying some weight”, “calm by shutdown”).
- Note: This layer is purely presentational and built in emotion_model.py.

Use this view for: **Quick story of each day** for humans.

### 3.2 Episode Recap (`episode_recaps.py` → `--recap`)

API:
```
build_episode_recap(episode_summary, day_summaries, characters)
```

**Example:**

```
EPISODE RECAP
==============================
The episode eases off; the early edge softens over time.
- Delta: Delta (optimizer) moved from high stress to low and gradually unwound. stayed strictly within guardrails.
- Nova: Nova (qa) moved from low stress to low and gradually unwound. stayed strictly within guardrails.
- Sprocket: Sprocket (maintenance) moved from mid stress to low and gradually unwound. stayed strictly within guardrails.
The shift winds down quietly, nothing pressing.
```

**How to interpret:**
* First line = **tension trend** over days:
  * rising → fire drill episode
  * falling → cooling / recovery
  * flat → routine stability
* Per-agent bullets:
  * **“moved from high stress to low”** → `stress_start` → `stress_end`
  * **“gradually unwound”** vs “held steady” vs “tightened” → shape of stress arc
  * Guardrail sentence mirrors `total_guardrail` vs `total_context`.

🔹 STORY ARC block
After the recap intro, the CLI now prints a STORY ARC block if EpisodeSummary.story_arc exists.

Fields displayed:
- arc_type
- tension_pattern
- supervisor_pattern
- emotional_color
- 3–6 short narrative lines

Computed deterministically via derive_episode_story_arc(...).

Example:
```
STORY ARC
---------
The episode opens tight and slowly unwinds.
Tension steps down each day.
The Supervisor stays mostly hands-off.
By the end, most of the floor feels drained rather than panicked.
```

🔹 MEMORY DRIFT block
A MEMORY DRIFT block may appear after STORY ARC.

It prints 0–3 short lines (at most one per agent).

Only prints when long-memory traits cross thresholds (agency ↑, trust ↓, reactivity ↑, stability ↓).

Driven by the additive AgentLongMemory computed in long_memory.py.

Example:
```
MEMORY DRIFT
------------
• Delta shows rising agency with steady footing.
• Sprocket’s trust in supervisor slips a little.
```

Use this view for: **High-level “previously on…”** episode summaries (good for dashboards, logs, UI top-level).

### 3.3 Daily Logs (`daily_logs.py` → `--daily-log`)

API:
```
build_daily_log(day_summary, previous_day_summary=None)
```

Outputs a `DailyLog` rendered as:

```
DAILY LOG
----------

Day 1
The floor begins calm and keeps easing off.
[Delta]
- Starts steady but alert — always chasing efficiency.
- Leans heavily on protocol.
- Stress eased compared to yesterday.
[Nova]
- ...
[Sprocket]
- ...
General:
- Supervisor stayed mostly quiet.
- Work skewed toward protocol.
- Overall stress eased a notch.
The day ends balanced and steady.
```

**How to interpret:**
This is basically a **shift report:**
* Agent bullets:
  * “Stress eased compared to yesterday” → comparison with previous day’s `avg_stress`.
  * Always uses protocol/context skew lines to reflect `guardrail_count` vs `context_count`.
* General section:
  * **Supervisor** line is a proxy for how often the supervisor acted vs broadcast.
  * **Work skewed toward protocol / context** → city-wide mode distribution.
  * **Overall stress drift** → aggregated stress change.
* Each agent now includes a single **Emotion** bullet derived from EA‑I:
  * Examples:
    * `Emotion: uneasy and unsure.`
    * `Emotion: calm but spent.`
  * Source: `_emotion_bullet(...)` based on mood/certainty/energy.

Use this view for:
**Ops-style analysis** – “what did the day look like from a shift lead’s POV?”

### 3.4 Agent Explainer (`explainer.py` → `explain-episode`)

API:
```
build_episode_context(...)
build_agent_focus_context(...)
explain_agent_episode(agent_context)
```

CLI:
```
uv run loopforge-sim explain-episode --steps-per-day 20 --days 3 --agent Delta
```

```
Example:

EPISODE EXPLAINER
==================
Agent: Delta

Delta (optimizer) spent this episode working under a easing factory tension profile.
As an optimizer, they are always watching throughput and deadlines.
Their stress gradually unwound, moving from high to moderate.
They stayed strictly within guardrails, rarely acting on raw context.
They managed to relax as the factory itself eased off.
```

**How to interpret:**
Designed for devs / ops, not players:
* First sentence: agent vs episode-wide tension.
* Second: role flavor from CHARACTERS.
* Third: stress arc: “tightened”, “gradually unwound”, or “held steady”.
* Fourth: guardrail vs context usage.
* Fifth: alignment between personal and global arcs (“relax as the factory eased off”).

Use this when you want to answer:
> “Is this robot burning out, coasting, or adapting?”

### 3.5 LLM Lens (`llm_lens.py` → `lens-agent`)

This is the **future-facing contract** for real LLMs.

API:
```
build_llm_perception_lens_input(day_summary, agent_name) -> LLMPerceptionLensInput
fake_llm_perception_lens(input) -> LLMPerceptionLensOutput

build_llm_episode_lens_input(episode_summary, characters, episode_id="ep-0")
fake_llm_episode_lens(input) -> LLMEpisodeLensOutput
```

CLI:
```
uv run loopforge-sim lens-agent --agent Delta --steps-per-day 20 --day-index 0
```

**Example:**

```
LLM PERCEPTION LENS (input)
-----------------------------
{
  "agent_name": "Delta",
  "role": "optimizer",
  "day_index": 0,
  "perception_mode": "accurate",
  "avg_stress": 0.35,
  "guardrail_count": 90,
  "context_count": 0,
  "tension": 0.36,
  "supervisor_tone_hint": "steady"
}

LLM PERCEPTION LENS (fake output)
----------------------------------
{
  "emotional_read": "under pressure and bound by protocol",
  "risk_assessment": "at risk of burnout",
  "suggested_focus": "increase autonomy where safe",
  "supervisor_comment_prompt": "Maintain pace; check assumptions before committing changes."
}
```

**How to interpret:**
* **Input struct** is the contract we’ll **freeze** before plugging in a real LLM.
* **Fake outputs** are rule-based now (deterministic), but show intended shape:
  * Emotion label
  * Risk label
  * Suggested adjustment lever
  * Suggested supervisor comment

In the future, `fake_llm_*` becomes:
* **Offline LLM calls** producing cached guidance
* Or **online calls** with strict timeouts + fallbacks

But the **input/output dataclasses stay stable.**

## 4. CLI Cheat Sheet

For future architects who just want to see stuff:

```bash
# 1. Run a short sim (no DB)
uv run loopforge-sim --no-db --steps 60

# 2. Numeric + narrative + recap + daily logs
uv run loopforge-sim view-episode \
  --steps-per-day 20 --days 3 \
  --narrative --recap --daily-log

# 3. Agent-focused psychological explainer
uv run loopforge-sim explain-episode \
  --steps-per-day 20 --days 3 --agent Delta

# 4. LLM lens input/output preview
uv run loopforge-sim lens-agent \
  --agent Delta --steps-per-day 20 --day-index 0


```

Flag map:
- `--narrative` → day intros + emotional overlay
- `--daily-log` → ops log + per-agent emotion bullets
- `--recap` → recap + STORY ARC + MEMORY DRIFT

Recommended workflow:
1. **First pass** – `view-episode` with no flags → sanity check stats.
2. **Second pass** – add `--recap` and `--narrative` → watch the episode like a story.
3. **Third pass** – for any “weird” agent, run `explain-episode` and `lens-agent`.

## 5. How to Read the Numbers as a Story
### 5.1 Tension

* `tension` per day ≈ “how sharp does the factory feel?”
  * > 0.4 → “edge”, “sharp”, “on the brink”
  * 0.15–0.4 → “steady with subtle edge”
  * < 0.15 → “calm”, “quiet hum”
* Trend:
  * Rising → something is brewing.
  * Falling → recovery / cooldown.
  * Flat high → chronic stress; future LLMs can call this out as “systemic risk”.

### 5.2 Stress Bands

Per agent `avg_stress` and `stress_start → stress_end`:
* **Low (< 0.08)** → essentially chill.
* **Mid (0.08–0.3)** → engaged, but safe.
* **High (> 0.3)** → tension, potential burnout.

Arcs:
* high → low = “unwound / decompressed”
* low → high = “tightened / under mounting pressure”
* similar → “held steady”

### 5.3 Guardrails vs Context

* `guardrail_count` >> `context_count`:
  * “Leans heavily on protocol / rulebook.”
  * Good for safety, bad for adaptation.
* `context_count` significant:
  * Later this will show up as “improvises / acts on instinct”.
This is the **main lever** for future LLM supervision:
increase autonomy where safe vs. clamp it down when tension is rising.

## 6. Where Real LLMs Will Plug In

This repo already has **hooks** designed:
1. **Perception Lens (Day-level)**
* Input: `LLMPerceptionLensInput`
* Output: `LLMPerceptionLensOutput`
* Usage: change supervisor messaging, adjust thresholds, or log richer “psychology” without touching the simulation core.
2. **Episode Lens (Episode-level)**
* Input: `LLMEpisodeLensInput`
* Output: `LLMEpisodeLensOutput`
* Usage: “season summary”, themes, risk flags, guidance for tuning parameters.

## Non-negotiables for future architects
* Keep simulation deterministic-ish; LLMs live in **side channels**, not inside the step loop.
* If you add real LLM calls:
  * Wrap them behind functions with **the same signatures** as `fake_llm_*`.
  * Provide **fallbacks** for test mode (either keep the fakes or use fixtures).
  * Never compute **core metrics** (stress, tension, mode counts) from text: those stay telemetry-driven.

## 7. Extending the Cinematic Debugger

If you’re the next architect on this project:
* Want new characters?
  * → Add them in `CHARACTERS` and watch them show up styled across views.
* Want more narrative flavor?
  * → Extend templates in `narrative_viewer.py` / `daily_logs.py` without changing inputs.
* Want LLM-guided supervision?
  * → Swap `fake_llm_*` with real calls, keep the dataclasses, and log both input and output for debugging.
* Want UI?
  * → These text blocks are already composable:
  * Day narrative = “story pane”
  * Daily log = “ops pane”
  * Explainer = “focus pane”
  * Lens = “LLM suggestion pane”

## 9. JSON Export (export-episode) — What You Get Now

What the export includes today:
- `days` (unchanged): per-day basics (tension, incidents, per-agent guardrails/context/stress).
- `agents` block now includes per-agent:
  - `trait_snapshot` (EA-III) — `{resilience, caution, agency, trust_supervisor, variance}`
  - `blame_timeline`
  - `blame_counts`
- New top-level fields:
  - `story_arc` (EA-II)
  - `long_memory` (EA-IV)

Short example shape (not a full dump):
```
{
  "days": [...],
  "agents": {
    "Delta": {
      "stress_start": 0.28,
      "stress_end": 0.09,
      "trait_snapshot": { "resilience": 0.49, "agency": 0.52, ... },
      "blame_timeline": ["random","system","system"],
      "blame_counts": { "random":1, "system":2, ... }
    }
  },
  "tension_trend": [...],
  "story_arc": { "arc_type": "decompression", ... },
  "long_memory": {
    "Delta": {
      "episodes": 1,
      "trust_supervisor": 0.52,
      "stability": 0.53,
      "agency": 0.48
    }
  }
}
```

Built via `analysis_api.analyze_episode(...)`.
Deterministic and read-only.

CLI example:
```
uv run loopforge-sim export-episode \
  --steps-per-day 20 --days 3 \
  --output logs/episode_export.json
```

## 8. TL;DR for Future You
* The cinematic debugger is an **observation rig**, not a control system (yet).
* Everything is built on **ActionLogEntry → DaySummary → EpisodeSummary.**
* Narratives, recaps, logs, explainers, and lenses are all **pure, deterministic, read-only layers.**
* We already have LLM-ready contracts; you just need to swap out the fake functions when you’re ready for real model calls.

Final consistency note:
All cinematic layers (narratives, logs, recaps, story-arc, trait snapshots, long-memory) are deterministic, telemetry-only, and never change simulation behavior. They interpret logs; they never alter actions.
* If you’re about to push a change that makes the output less interesting to read, stop and ask:
> “Would The Producer yell at me for making this more boring?”

If the answer is yes, walk it back and add more style.