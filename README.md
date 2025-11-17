# 🌆 Loopforge — What This Project Really Is

Loopforge is a robot drama machine. It’s built with a storytelling‑first philosophy: we simulate days to cut episodes that are surprising to watch and easy to explain. Every narrative layer is deterministic and telemetry‑driven so that what you see can be audited and reasoned about by engineers and future AI. Start with the vision to understand the creative North Star that guides all technical choices.

[Full Producer Vision → docs/PRODUCER_VISION.md]

# Loopforge City

# LOOPFORGE LLM BUILDER PROMPT
(Read this before you touch anything, robot friend.)

For future LLM-based system architects and planners, start here:
- docs/LOOPFORGE_AGENT_PROMPT.md — the canonical system prompt/design brief that explains the philosophy, north star, and phased workflow expected in this repository. Read it before proposing changes.
- docs/ARCHITECTURE_EVOLUTION_PLAN.md — the architecture evolution plan (now including the “Next 10 Phases” — Phase 4–13); use it to stage incremental changes (policy seam, mode logging, reflections, etc.).
- docs/STATELOG.md — rolling repository snapshot (timestamp, HEAD, recent commits, test status) to help you reorient quickly.

A small, text-based multi-agent simulation scaffold. Three robots plus a Supervisor act over discrete steps; state persists to PostgreSQL via SQLAlchemy with Alembic migrations. The app is containerized and uses `uv` for Python env and dependency management.

---

## LLM-friendly project overview (what, where, why)

This repository is intentionally structured to be easy for both humans and LLMs to understand, extend, and test. The design separates concerns so you can safely modify one layer without breaking others.

Key ideas:
- Environment owns hard state and rules (facts, numbers, DB writes) — agents never mutate DB directly.
- Agents decide actions through a clear seam (Perception → ActionPlan). Today the plan is deterministic; later it can be LLM-driven without changing the simulation loop.
- Simulation orchestrates steps, applies rules, persists rows, and prints concise logs.

Primary modules and contracts:
- loopforge/types.py
  - Core types (Phase 1): `AgentPerception`, `AgentActionPlan`, `AgentReflection` with `to_dict`/`from_dict` roundtrips. Re‑exported in `loopforge.__init__` for convenience. These are structural only at this stage (no behavior change) and will be used by later phases (policy seam, narrative wiring, reflections).
- loopforge/simulation.py
  - run_simulation(num_steps=10, persist_to_db=None)
  - Drives each step: build agents from DB (or in-memory), call policies, update locations/battery, compute context, update emotions, evaluate triggers, persist ActionLog/Memory, derive EnvironmentEvent(s), invoke Supervisor.
  - Contract: Pure orchestrator; assumes policy functions follow a stable action dict schema.
- loopforge/agents.py
  - RobotAgent(name, role, location, battery_level, emotions, traits, triggers)
    - decide(step) -> dict  (delegates to llm_stub.decide_robot_action)
    - run_triggers(env) -> None
  - SupervisorAgent
    - decide(step, summary) -> dict (delegates to llm_stub.decide_supervisor_action)
  - Trigger(name, condition(agent, env), effect(agent, env))
  - Why: Encapsulates transient per-step agent state and behavioral hooks separate from persistence.
- loopforge/emotions.py
  - EmotionState + clamp; Traits + clamp
  - update_emotions(agent, last_action: dict, context: dict)
  - ORM sync helpers: emotion_from_robot, apply_emotion_to_robot, traits_from_robot, apply_traits_to_robot
  - Why: Keep affective/trait logic small, explicit, and testable; DB code stays elsewhere.
- loopforge/environment.py
  - LoopforgeEnvironment: rooms, step counter, events buffer, recent_supervisor_text; advance/drain/record methods
  - generate_environment_events(env, session) -> list[EnvironmentEvent]
  - Why: Derive world events from recent actions/stress deterministically; returns objects, simulation decides when to add/commit.
- loopforge/narrative.py
  - AgentPerception: what the agent “sees” (structured snapshot + short textual summaries)
  - AgentActionPlan: what the agent intends to do (intent/move_to/targets/riskiness + narrative)
  - build_agent_perception(agent, env, step)
  - Perception modes: `perception_mode` is present (Phase 4b) and currently set to "accurate"; future phases may use "partial" or "spin".
  - Why: A clean seam for LLM prompts later without rewriting the loop; used directly by the deterministic policy path in simulation.
- loopforge/llm_stub.py
  - decide_robot_action(...) and decide_supervisor_action(...): stable public API used by the simulation
  - Internally: builds Perception → creates an ActionPlan → adapts back to the legacy action dict schema; optional LLM path behind USE_LLM_POLICY with safe fallback
  - Why: Preserve old contracts while enabling narrative/LLM evolution.
- loopforge/reflection.py
  - summarize_agent_day(entries)
  - build_agent_reflection(agent_name, role, summary) -> AgentReflection
  - apply_reflection_to_traits(traits_or_agent, reflection) -> Traits | None (tiny, clamped nudges)
  - run_daily_reflection_for_agent(agent, entries) -> AgentReflection
  - Why: Opt-in analysis layer for end-of-day reflections and small trait evolution; not wired into the main loop yet (Phase 5).
- loopforge/models.py + loopforge/db.py
  - SQLAlchemy models (Robot, Memory, ActionLog, EnvironmentEvent) and DB utilities (Base, get_engine, session_scope)
  - Why: Single source of persistence truth; simulation orchestrates commit boundaries via session_scope.
- scripts/run_simulation.py (Typer CLI)
  - loopforge-sim entrypoint. Does not contain domain logic; resolves steps and persistence mode and calls run_simulation.

Data flow in a step (DB-backed):
1) Load Robot rows → build RobotAgent(s) using emotion/trait helpers.
2) For each agent: Perception → ActionPlan → action dict; simulation applies location/battery changes.
3) Compute context flags → update_emotions → run_triggers → persist updated emotions/traits to the same Robot row.
4) Write ActionLog + Memory (Memory.text embeds a short “Plan:” narrative for later analysis).
5) Drain buffered events; derive new events with generate_environment_events and add them.
6) Supervisor decides next action; action is logged; env.recent_supervisor_text is updated (used by triggers next step).

Testing philosophy:
- Unit tests cover config flags, LLM wrappers (mocked), perception/plan generation, emotion updates, triggers, and the deterministic event engine.
- Integration tests cover simulation in no‑DB mode and DB-backed mode using a temporary SQLite engine via monkeypatch (fast, offline, deterministic).

## Quickstart

Most local runs should be containerized (app + db). For a super-fast local smoke test without touching any database, use the no-DB mode.

### A) Local quick test (no DB)

This runs entirely in memory and prints step summaries to stdout; nothing is written to a database.

```bash
make uv-sync    # first time only, to install deps locally
make run        # runs 10 steps with --no-db
```

- You can change the number of steps with the CLI, e.g. `uv run loopforge-sim --no-db --steps 5` or by editing the Makefile target.
- This mode ignores any database settings and requires no Postgres running locally.

#### View a day from JSONL logs (dev cockpit)

After you run the sim (no‑DB or DB), you can summarize a single day directly from the JSONL action log. This reads logs only — no UI, just clean text.

```bash
make run-day                    # summarizes Day 0 by default from logs/loopforge_actions.jsonl
uv run loopforge-sim view-day   # same as make target
```

Options:
- `--day-index N` choose which day to view (0-based)
- `--steps-per-day 50` if your day size differs
- `--action-log-path PATH` to point at a different JSONL file
- `--reflection-log-path PATH` to also write reflections JSONL
- `--supervisor-log_path PATH` to also write supervisor JSONL

Example output:
```
Day 0 — Summary
=========================

Sprocket (maintenance)
- Intents: work (7), inspect (2), recharge (1)
- Emotions: stress=0.71, curiosity=0.54, satisfaction=0.33
- Reflection: "I plan to keep the line running..."

Supervisor
- Messages: "encourage_context", "neutral_update"
```

### B) Containers: app + db (recommended for normal runs)

Prereqs: Docker and docker-compose installed.

1) Build and start Postgres + app containers (detached):
```bash
make docker-up
```
This will:
- start a local PostgreSQL container (`db`)
- build the app image if needed
- run Alembic migrations automatically inside the app container
- start the simulation for `SIM_STEPS` (default: 10)

2) Stream logs from both services:
```bash
make docker-logs
```

3) Change the number of steps (override `SIM_STEPS` at launch):
```bash
SIM_STEPS=25 make docker-up
# re-run logs if needed:
make docker-logs
```

4) Stop and remove containers and volumes when done:
```bash
make docker-down
```

Notes:
- Base image: official uv image `ghcr.io/astral-sh/uv:python3.14-bookworm` (uv and Python preinstalled; smaller, faster, more reproducible builds).
- The container uses uv to create and manage a project-local virtual environment at `/app/.venv` during build (`uv sync --frozen`, honoring `uv.lock`).
- Migrations run automatically inside the app container before starting the simulation.
- No local `DATABASE_URL` needed for this flow; the compose file wires the app to the `db` service.
- The app inside the container uses `PERSIST_TO_DB=true` by default; local no-DB runs set `--no-db` automatically via the Makefile.
- You can adjust other env vars by prefixing the `make` call, e.g. `LOG_LEVEL=DEBUG make docker-up`.
- Compose command variants: if your system only has the v2 plugin (`docker compose`), either run those commands directly or override the Makefile variable once, e.g. `make DC="docker compose" docker-up`.

## Architecture overview

### Stack overview
- Runtime: Python 3.14 (container) using the official uv base image `ghcr.io/astral-sh/uv:python3.14-bookworm`.
- Dependency/env management: uv with a project-local virtualenv at `/app/.venv` inside the container; `uv.lock` ensures reproducible builds.
- Database: PostgreSQL 16 (container), accessed via SQLAlchemy 2.x ORM.
- Migrations: Alembic, auto-applied on container start (`alembic upgrade head`).
- CLI: Typer app exposed as `loopforge-sim`.
- Orchestration: Docker Compose (services `app` and `db`).

### Implementation layers and contracts

The project is intentionally layered and minimal. Most logic flows top→down:

1) CLI entrypoint (`scripts/run_simulation.py`)
   - Method: `main(steps: int | None, no_db: bool)` → parses CLI, resolves steps and persistence mode, calls `loopforge.simulation.run_simulation`.
   - Contract: Does not contain domain logic. It only selects mode and delegates.

2) Simulation loop (`loopforge/simulation.py`)
   - Method: `run_simulation(num_steps: int = 10, persist_to_db: bool | None = None)`
     - No-DB mode: builds in-memory `RobotAgent`s and runs a quick loop without touching the DB.
     - DB-backed mode: opens a SQLAlchemy session via `session_scope`, seeds robots if needed, and for each step:
       - Loads `Robot` rows, constructs `RobotAgent`s, runs decisions, updates world state (location, battery),
         computes context flags, updates emotions (`update_emotions`) and triggers (`agent.run_triggers`),
         persists state back to the corresponding `Robot` row, and writes `ActionLog` + `Memory` entries.
       - Buffers environment events (`env.record_event`), then calls `generate_environment_events` to derive
         events from recent actions/stress; adds them and commits.
     - Contracts:
       - Uses only public helpers from `agents.py`, `emotions.py`, `environment.py`.
       - ORM writes go through SQLAlchemy `Session` inside `session_scope()`.
       - Supervisor actions are logged to `ActionLog` with `actor_type="supervisor"` and also exposed to
         robot triggers via `env.recent_supervisor_text`.

3) Agents and triggers (`loopforge/agents.py`)
   - Classes:
     - `RobotAgent`: transient step-time representation with fields `name`, `role`, `location`, `battery_level`,
       `emotions: EmotionState`, `traits: Traits`, `triggers: list[Trigger]`.
       - Methods:
         - `decide(step) -> dict`: delegates to `llm_stub.decide_robot_action` (deterministic placeholder).
         - `run_triggers(env) -> None`: evaluates each `Trigger` after emotions update; guards against exceptions.
     - `SupervisorAgent`: minimal policy with `decide(step, summary) -> dict`, delegating to `llm_stub.decide_supervisor_action`.
     - `Trigger` (dataclass):
       - `name: str`
       - `condition(agent, env) -> bool`
       - `effect(agent, env) -> None`
   - Presets:
     - `default_traits_for(name) -> Traits`: initial trait profiles for Sprocket/Delta/Nova.
     - `default_triggers_for(name) -> list[Trigger]`:
       - Sprocket “Crash Mode”: fires when stress > 0.8 and recent supervisor message mentions "hurry"; lowers `risk_aversion` slightly and bumps stress.
       - Nova “Quiet Resentment”: fires when stress > 0.6 and satisfaction < 0.3; increases `blame_external`, reduces `obedience` slightly.
   - Contracts:
     - Trigger effects only mutate the agent’s emotions/traits; persistence is handled by the simulation layer via helpers.

4) Emotions and traits (`loopforge/emotions.py`)
   - Dataclasses:
     - `EmotionState`: `stress`, `curiosity`, `social_need`, `satisfaction`; `clamp()` keeps values within [0,1].
     - `Traits`: `risk_aversion`, `obedience`, `ambition`, `empathy`, `blame_external`; `clamp()` bounds values.
   - Functions:
     - `update_emotions(agent, last_action: dict, context: dict) -> None`:
       - Applies baseline drift each step (stress/social_need down slightly; curiosity up slightly).
       - Action-driven nudges: `work`, `recharge`, `talk`, `move`, `inspect`.
       - Context flags: `near_error` (stress+curiosity up), `isolated` (social_need up, satisfaction down slightly).
       - Clamps at the end.
     - ORM sync helpers:
       - `emotion_from_robot(robot) -> EmotionState`
       - `apply_emotion_to_robot(robot, emotions) -> None`
       - `traits_from_robot(robot) -> Traits`
       - `apply_traits_to_robot(robot, traits) -> None`
   - Contracts:
     - Stateless helpers; no direct DB access.
     - Update logic is small and deterministic, safe to call each step.

5) Environment and events (`loopforge/environment.py`)
   - Class: `LoopforgeEnvironment` with `rooms`, `step`, `events_buffer`, `recent_supervisor_text`.
     - Methods: `advance()`, `record_event(type, location, description)`, `drain_events()`.
   - Function: `generate_environment_events(env, session) -> list[EnvironmentEvent]`:
     - Heuristic: looks at Sprocket’s last action and stress, and recent errors at that location; with a small
       deterministic chance, emits an `Incident`. Also occasionally emits `MinorError` to keep the world lively.
   - Contracts:
     - Event derivation is side-effect free: returns new `EnvironmentEvent` objects without committing.
     - Simulation decides when to `session.add()` and commit.

6) Models and DB (`loopforge/models.py`, `loopforge/db.py`)
   - ORM models:
     - `Robot`: core state incl. `traits_json` and current emotions.
     - `Memory`: per-step text notes for robots.
     - `ActionLog`: actions for robots and supervisor (nullable `robot_id` for supervisor).
     - `EnvironmentEvent`: events derived from environment or heuristic engine.
   - DB utilities:
     - `Base` (DeclarativeBase), `get_engine()`, and `session_scope()` context manager.
   - Contracts:
     - All DB interactions in the simulation occur inside `session_scope()` to ensure commit/rollback safety.

7) Decision stubs (`loopforge/llm_stub.py`)
   - Functions:
     - `decide_robot_action(...) -> dict` : deterministic policy by role and step.
     - `decide_supervisor_action(step, summary) -> dict` : broadcasts every 4th step; coaches on “high stress”; otherwise inspects.
   - Contract: Pure function stubs suitable for replacement by real AI/LLM policy later.

### Data flow (DB-backed step)
1. Load `Robot` rows (excluding supervisor) → build `RobotAgent`s using `emotion_from_robot` / `traits_from_robot`.
2. Each agent decides an action → simulation updates location/battery.
3. Build context flags → `update_emotions(agent, last_action, context)` → `agent.run_triggers(env)`.
4. Persist back: `apply_emotion_to_robot` + `apply_traits_to_robot` on the same `Robot` row.
5. Append `ActionLog` and `Memory` rows for each agent.
6. Drain buffered env events; then call `generate_environment_events` and add those events.
7. Decide supervisor action; log it; expose text as `env.recent_supervisor_text` for next-step triggers.

---

## Configuration

Environment variables (container-first):
- `LOG_LEVEL` (default: `INFO`) – adjust verbosity (e.g., `LOG_LEVEL=DEBUG make docker-up`).
- `SIM_STEPS` (default: `10`) – number of simulation steps for the app container.
- `PERSIST_TO_DB` (default: `true` in containers) – controls DB persistence; local `make run` uses `--no-db` regardless.
- `ECHO_SQL` (default: `false`) – set to `true` to echo SQL statements from SQLAlchemy.
- `USE_LLM_POLICY` (default: `false`) – when `true` and an API key is provided, robot/supervisor decisions use an LLM instead of the deterministic stub.
- `LLM_MODEL_NAME` (default: `gpt-4.1-mini`) – model name passed to the OpenAI client.
- `OPENAI_API_KEY` (optional) – required only when `USE_LLM_POLICY=true`.

Notes:
- You do NOT need to set `DATABASE_URL` for container runs; compose wires the app to `db` internally.
- For local no-DB runs (`make run`), the database is not used at all.
- LLM usage is fully optional. By default, the simulation uses deterministic stub policies; set `USE_LLM_POLICY=true` and provide `OPENAI_API_KEY` to enable LLM-driven decisions.
- Advanced: if you intentionally run the app against a locally managed Postgres outside containers, see `CONTRIBUTING.md` for manual Alembic usage and supply `DATABASE_URL` yourself.

The app reads environment variables in `loopforge/config.py`.

---

## Seam, logs, and day orchestrators (Phases 4–8)

This project follows a strict decision seam:

```text
Environment (truth)
 → AgentPerception (subjective slice; has perception_mode)
 → Policy (stub or LLM)
 → AgentActionPlan (intent/move_to/targets/riskiness/mode/narrative)
 → Legacy action dict (public shape)
 → Environment (truth updated)
```

### JSONL logs (fail‑soft)
- Action logs (Phase 4):
  - One JSON object per non‑LLM decision step via `log_action_step(...)`.
  - Path precedence: explicit `run_simulation(..., action_log_path=...)` > `ACTION_LOG_PATH` env var > default `logs/loopforge_actions.jsonl`.
  - Reader helper: `logging_utils.read_action_log_entries(path)` (fail‑soft; skips malformed lines).
- Reflection logs (Phase 6):
  - Written by `JsonlReflectionLogger` (used by the day runner). Includes additive `perception_mode` field (Phase 8).
  - Provide a path via `day_runner.run_one_day(..., reflection_logger=JsonlReflectionLogger(path))` or `reflection_log_path` in the supervisor orchestrator.
- Supervisor logs (Phase 7):
  - Written by `JsonlSupervisorLogger` as one line per message.
  - Path precedence: `SUPERVISOR_LOG_PATH` env var > explicit `supervisor_log_path` parameter > default `logs/loopforge_supervisor.jsonl`.
  - Logging is fail‑soft and must not crash the orchestrator.

### Perception modes (Phase 8 — opt‑in)
- Configure with `PERCEPTION_MODE` env var; allowed values: `accurate` (default), `partial`, `spin`.
- Helper: `config.get_perception_mode()` normalizes unknown values back to `"accurate"`.
- Shaping layer: `perception_shaping.shape_perception(perception, env)` is invoked inside `narrative.build_agent_perception(...)`.
  - `accurate`: no change.
  - `partial`: truncates `local_events` and shortens `world_summary` (no fabricated facts).
  - `spin`: tone‑shifts summaries based on recent supervisor guidance (e.g., emphasize risk when protocols tighten). Truth/DB remain untouched.
- Reflections are tagged with the active `perception_mode`; `ReflectionLogEntry` includes this field.

### Day runner helpers (Phase 6–7)
Two opt‑in helpers compose runs over a “day” (a window of steps) using the JSONL action log:

- `day_runner.run_one_day(env, agents, steps_per_day=50, day_index=0, reflection_logger=None, action_log_path=Path("logs/loopforge_actions.jsonl")) -> list[AgentReflection]`
  - Advances the env for `steps_per_day` if it has `step()`, slices action entries for the day, runs reflections for all agents, and optionally logs them.
- `day_runner.run_one_day_with_supervisor(env, agents, steps_per_day=50, day_index=0, action_log_path=..., reflection_log_path=None, supervisor_log_path=None, reflection_logger=None) -> list[SupervisorMessage]`
  - Calls `run_one_day(...)`, builds `SupervisorMessage` objects from reflections, logs them (fail‑soft), and publishes them onto `env` for the next day via `set_supervisor_messages_on_env`.
  - Messages show up in subsequent perceptions through `AgentPerception.recent_supervisor_text`.

Quick example (no DB, contrived env/agents):

```python
from pathlib import Path
from types import SimpleNamespace
from loopforge.day_runner import run_one_day_with_supervisor

class Env:
    def step(self):
        pass

env = Env()
agents = [SimpleNamespace(name="A", role="maintenance", traits={})]

# Suppose logs/loopforge_actions.jsonl already has some entries for agent A
msgs = run_one_day_with_supervisor(
    env=env,
    agents=agents,
    steps_per_day=50,
    day_index=0,
    action_log_path=Path("logs/loopforge_actions.jsonl"),
    supervisor_log_path=Path("logs/loopforge_supervisor.jsonl"),
)
print([m.intent for m in msgs])
```

See `docs/ARCHITECTURE_EVOLUTION_PLAN.md` for the full phased roadmap and `docs/JUNIE_SYSTEM_PROMPT.md` for the engineering covenant that guides changes.

## Episodes, Metrics & Weave (Phases 9–10 Lite)

These layers are additive, pure, and log-powered. They do not change the simulation or DB schemas.

### Episodes (indexing and orchestration)
- Additive labels on logs (nullable by default):
  - `ActionLogEntry.episode_index: int | None`, `ActionLogEntry.day_index: int | None`
  - `ReflectionLogEntry.episode_index: int | None` (day index already present)
  - `SupervisorMessage.episode_index: int | None`
- Orchestrator:
  - `day_runner.run_episode(env, agents, num_days, steps_per_day, *, persist_to_db, episode_index=0, action_log_path=None, reflection_log_path=None, supervisor_log_path=None)`
  - Delegates to `run_one_day_with_supervisor(...)` for each day, threading `(episode_index, day_index)` into reflection and supervisor logs.

Minimal example:
```python
from pathlib import Path
from types import SimpleNamespace
from loopforge.day_runner import run_episode

class Env:
    def step(self):
        pass

env = Env()
agents = [SimpleNamespace(name="A", role="maintenance", traits={})]

run_episode(
    env=env,
    agents=agents,
    num_days=2,
    steps_per_day=3,
    persist_to_db=False,
    episode_index=7,
    action_log_path=Path("logs/loopforge_actions.jsonl"),
    reflection_log_path=Path("logs/reflections.jsonl"),
    supervisor_log_path=Path("logs/loopforge_supervisor.jsonl"),
)
```

### Metrics Harness (pure helpers)
Module: `loopforge/metrics.py`.

- Readers (fail‑soft):
  - `read_action_logs(path) -> list[ActionLogEntry]`
  - `read_reflection_logs(path) -> list[ReflectionLogEntry]`
  - `read_supervisor_logs(path) -> list[dict]`
- Metric helpers:
  - `compute_incident_rate(actions)` → `{incident_rate, total_steps, incidents}`
  - `compute_mode_distribution(actions)` → counts + normalized `distribution`
  - `compute_perception_mode_distribution(reflections)`
  - `compute_supervisor_intent_distribution(reflections)` (uses perceived labels from reflections)
  - `compute_belief_vs_truth_drift(actions, reflections)` (v1 drift proxy via `perception_mode`)
  - Segmenters: `segment_by_episode(actions)`, `segment_by_day(actions)`
- Optional CLI: `scripts/metrics.py` (Typer)
  - Incidents: `uv run python -m scripts.metrics incidents --actions logs/loopforge_actions.jsonl`
  - Modes: `uv run python -m scripts.metrics modes --actions logs/loopforge_actions.jsonl`
  - Perception modes: `uv run python -m scripts.metrics pmods --reflections logs/reflections.jsonl`
  - Drift: `uv run python -m scripts.metrics drift --actions logs/loopforge_actions.jsonl --reflections logs/reflections.jsonl`

### Weave (episode tension snapshots)
- Core type: `EpisodeTensionSnapshot` with JSON round‑trip (`loopforge/types.py`).
- Compute from logs (pure): `loopforge/weave.py`
  - `compute_episode_tension_snapshot(episode_index, actions, reflections) -> EpisodeTensionSnapshot`
  - `compute_all_episode_snapshots(actions, reflections) -> list[EpisodeTensionSnapshot]`
- JSONL writer: `JsonlWeaveLogger` in `loopforge/logging_utils.py` writes one snapshot per line (fail‑soft) to a separate file (e.g., `logs/loopforge_weave.jsonl`).

Example (derive and write one snapshot):
```python
from pathlib import Path
from loopforge.metrics import read_action_logs, read_reflection_logs
from loopforge.weave import compute_all_episode_snapshots
from loopforge.logging_utils import JsonlWeaveLogger

actions = read_action_logs("logs/loopforge_actions.jsonl")
reflections = read_reflection_logs("logs/reflections.jsonl")
snaps = compute_all_episode_snapshots(actions, reflections)
logger = JsonlWeaveLogger(Path("logs/loopforge_weave.jsonl"))
for s in snaps:
    logger.write_snapshot(s)
```

Notes:
- All of the above are optional and can be used offline.
- Default runs behave exactly as before; new fields are nullable and logging remains fail‑soft.

### Story Arc, Trait Drift & Long Memory (EA-II–IV, deterministic)

Higher-order episode structure and slow character memory sit purely on the analysis side. They never change how the sim runs; they only decorate `EpisodeSummary`, recaps, and exports.

- **Episode Story Arc (`EpisodeStoryArc`)**
  - **Type:** `EpisodeStoryArc { arc_type, tension_pattern, supervisor_pattern, emotional_color, summary_lines }`
  - **Engine:** `loopforge/story_arc.py::derive_episode_story_arc(episode_summary)`
  - **Inputs:** per-day tension, supervisor activity, per-day emotion states.
  - **Where it shows up:**
    - `EpisodeSummary.story_arc` (optional).
    - CLI `view-episode --recap`: **STORY ARC** block with 3–6 deterministic summary lines.
    - JSON export: root `"story_arc"` dict.

- **Trait Drift (`trait_snapshot` per agent)**
  - **Type:** additive `trait_snapshot: Dict[str, float]` on `AgentEpisodeStats` with keys like `resilience`, `caution`, `agency`, `trust_supervisor`, `variance`.
  - **Engine:** `loopforge/trait_drift.py::derive_trait_snapshot(...)`  
    Small clamped steps (≈0.02–0.05) based on:
    - stress start→end for the episode,
    - guardrail vs context reliance,
    - dominant attribution cause(s),
    - belief drift and story arc.
  - **Where it shows up:**
    - `summary.agents[name].trait_snapshot` in memory.
    - JSON export: per-agent `"trait_snapshot"` dict.

- **Episode Long Memory (`AgentLongMemory`)**
  - **Type:** `AgentLongMemory { episodes, cumulative_stress, cumulative_incidents, trust_supervisor, self_trust, stability, reactivity, agency }`
  - **Engine:** `loopforge/long_memory.py::update_long_memory_for_agent(...)`  
    - Aggregates stats across episodes (episodes count, cumulative stress/incidents).
    - Updates identity-like axes via tiny, clamped steps driven by blame mix, stress arc, guardrail vs context, and attribution diversity.
  - **Where it shows up:**
    - `EpisodeSummary.long_memory[name]` (optional).
    - CLI `view-episode --recap`: **MEMORY DRIFT** block (up to 3–4 lines like “Delta: growing more sure-footed with each shift.”) when thresholds are crossed.
    - JSON export: root `"long_memory"` dict keyed by agent.

All of these are **read-only, deterministic** and hang off `EpisodeSummary`; the sim loop and JSONL step logs remain unchanged.

## Testing & Coverage

- Run all tests locally:
  ```bash
  make uv-sync
  make test
  ```
- Run with coverage and see missing lines:
  ```bash
  make test-cov
  ```
- Run tests inside the container (optional):
  ```bash
  docker compose run --rm app uv run pytest -q
  ```

## Common tasks (Makefile)

```bash
make uv-sync       # uv sync --extra dev
make migrate       # alembic upgrade head
make run           # run the simulation locally (10 steps)
make run-all       # migrate then run
make revision NAME="message"   # create a new Alembic revision
make downgrade-one # alembic downgrade -1
make docker-up     # docker-compose up --build -d
make docker-logs   # tail logs
make docker-down   # docker-compose down -v
# commit tooling
git config commit.template .gitmessage
make hooks-install # install commit-msg hook (Commitizen check)
make cz-commit     # interactive commit
make cz-check      # check last commit message
make cz-bump       # bump version + tag
```

## Database & migrations

- Models live in `loopforge/models.py`.
- Alembic is configured in `alembic/` with an initial migration in `alembic/versions/0001_initial.py`.
- Typical workflow after changing models:
  ```bash
  # Using Makefile shortcuts
  make revision NAME="describe change"
  make migrate

  # Or raw uv commands (advanced/manual)
  uv run alembic revision --autogenerate -m "describe change"
  uv run alembic upgrade head
  ```

### Alembic versions

- `0001_initial`:
  - Creates base tables: `robots`, `memories`, `action_logs`, `environment_events`.
  - Sets initial server defaults for emotion columns (`stress=0.2`, `curiosity=0.5`, `social_need=0.5`, `satisfaction=0.5`).
- `0002_traits_and_defaults`:
  - Adds `robots.traits_json` to persist per-robot `Traits`.
  - Changes server default for `robots.social_need` from `0.5` → `0.3` (affects new inserts only; existing rows keep values).

Notes:
- Migrations are applied automatically inside the app container at startup (`alembic upgrade head`).
- If you add/modify ORM models, generate a new revision and apply it (see commands above). For deterministic container builds, commit the new migration into `alembic/versions/`.

## Development notes

- Decision stubs are in `loopforge/llm_stub.py`.
- Supervisor is represented as a `Robot` row for simpler logging.
- Emotions are simple placeholders in `loopforge/emotions.py`.
- Commit messages follow Conventional Commits; see `CONTRIBUTING.md` for details. A ready-to-use template is in `.gitmessage`, and commit hooks are configured via `.pre-commit-config.yaml`.

## Project layout

```
loopforge/
  config.py, db.py, models.py, emotions.py, memory_store.py,
  agents.py, environment.py, simulation.py, llm_stub.py
scripts/
  run_simulation.py
alembic/
  env.py, script.py.mako, versions/0001_initial.py
Dockerfile, docker-compose.yml, alembic.ini, pyproject.toml, README.md
```

## Troubleshooting

- uv not found in `make`: ensure `$HOME/.local/bin` is on PATH or run `PATH="$HOME/.local/bin:$PATH" make uv-sync`.
- Connection issues: verify `DATABASE_URL` and that Postgres is running (`docker ps` or `pg_isready`).
- psycopg URL scheme: use `postgresql+psycopg://...` (psycopg 3).


---

## Current capabilities (snapshot)
- Deterministic step-based simulation with three robots (Sprocket, Delta, Nova) and a Supervisor.
- Emotions and traits tracked per robot with simple update heuristics and clamped ranges.
- Triggers evaluated after emotions (e.g., Sprocket “Crash Mode”, Nova “Quiet Resentment”).
- Minimal event engine derives `Incident`/`MinorError` from recent actions and stress.
- Narrative layer (Phase 1): Environment builds `AgentPerception`; policy produces an `AgentActionPlan` with a short narrative; simulation persists the narrative into `Memory` ("Plan: ...").
- Optional LLM decision mode behind a feature flag with safe fallback to deterministic policies.
- Pytest suite covering config flags, LLM wrapper, narrative layer, emotions, triggers, event engine, and both simulation modes.
- Read-only diagnostic stack for Beliefs, Emotion, Story Arc, Trait Drift, and Long Memory, surfaced via `view-episode` recaps and `export-episode` JSON.

## LLM decision mode (optional)
The project runs deterministically by default. To let an LLM propose next actions (robots and supervisor) while keeping the same contracts and safe fallback:

Required env vars
- `USE_LLM_POLICY=true`
- `OPENAI_API_KEY=<your key>`
- optional: `LLM_MODEL_NAME` (default `gpt-4.1-mini`)

Local (no DB, just to see decisions change)
```bash
USE_LLM_POLICY=true OPENAI_API_KEY=sk-... uv run loopforge-sim --no-db --steps 5
```

Containers (DB-backed)
```bash
USE_LLM_POLICY=true OPENAI_API_KEY=sk-... make docker-up
make docker-logs
```
If the model response is invalid or the API is unavailable, the code automatically falls back to the deterministic stub for that decision.

## Where to add new behavior
- New triggers: `loopforge/agents.py` → extend `default_triggers_for(name)` or attach at runtime.
- New emotion/context rules: `loopforge/emotions.py` → adjust `update_emotions` or add helpers.
- New event heuristics: `loopforge/environment.py` → update `generate_environment_events` (keeps DB-agnostic behavior; return objects for the simulation to persist).
- Richer narrative prompts or parsing: `loopforge/narrative.py` and `loopforge/llm_stub.py` → expand `AgentPerception`/`AgentActionPlan` and the adapters without touching the loop.
- DB schema evolution: `loopforge/models.py` then create a migration via `make revision NAME="..."` and `make migrate`.



---

## Belief Layer v0.1 (read-only, deterministic)

A new, deterministic Belief Layer is computed at summary time from telemetry and attached to each `DaySummary` as `beliefs: Dict[str, BeliefState]` (keyed by agent name). It is strictly read-only and does not affect simulation behavior.

- What it is: a per-agent `BeliefState` snapshot derived from day metrics (no randomness, no LLM). Fields:
  - `supervisor_trust` (0..1)
  - `guardrail_faith` (0..1)
  - `self_efficacy` (0..1)
  - `world_predictability` (0..1)
  - `incident_attribution` in {`self`, `world`, `supervisor`, `random`}
- Where it appears:
  - Day Narrative: appends a one-line belief tagline per agent (e.g., “slipping confidence”, “renewed reliance on the manual”).
  - Daily Log: adds a compact “Belief:” line (e.g., “leaning on guardrails; confidence stable.”).
  - Episode Recap: adds “Belief drift: supervisor trust {start} → {end}.” per agent.
- How it’s computed: `loopforge/beliefs.py::derive_belief_state(...)` applies ±0.05 step rules (clamped 0..1) using guardrail/context counts, incidents, stress deltas, supervisor activity, and day tension. Integrated in `loopforge/reporting.py::summarize_day(...)`.
- Tests: see `tests/test_beliefs.py` for deterministic, synthetic cases.
- Further reading: `docs/DIAGNOSTIC_PHILOSOPHY.md` and `docs/COGNITIVE_ARCHITECTURE_SPEC.md`.

This layer is additive and telemetry-only; it does not change actions, policies, or logs schemas.

## Cinematic Debugger — Watch Days and Episodes (read-only over logs)

This repository now includes a developer-facing “cinematic debugger” that turns telemetry into readable story-like summaries. It is pure, deterministic, and does not change simulation behavior. Detailed docs live in `docs/CINEMATIC_DEBUGGER.md`.

Key layers (all read-only, telemetry-only):
- Day Narratives: `--narrative` (per-day story beats)
- Episode Recaps: `--recap` (episode-level intro + per-agent blurbs)
- When long-memory is present, `--recap` also prints a **MEMORY DRIFT** block: 1–4 deterministic lines summarizing how each agent’s long-term trust/agency/stability is drifting.
- Daily Narrative Logs: `--daily-log` (ops-style daily shift report)
- Agent Explainer: `explain-episode` (short, deterministic paragraph for one agent)
- LLM Lens (scaffolding): `lens-agent` (typed inputs + deterministic fake outputs)

### Watch an episode from logs (multi-day)

Use the CLI to read JSONL logs and render an episode summary. Numbers come from `ActionLogEntry → DaySummary → EpisodeSummary` only.

```bash
# Basic episode view (numeric per-day blocks + character sheets)
uv run loopforge-sim view-episode --steps-per-day 20 --days 3

# Add day-level story snippets
uv run loopforge-sim view-episode --steps-per-day 20 --days 3 --narrative

# Add episode recap + per-agent spotlights
uv run loopforge-sim view-episode --steps-per-day 20 --days 3 --recap

# Add ops-style daily logs
uv run loopforge-sim view-episode --steps-per-day 20 --days 3 --daily-log

# Combine all three
uv run loopforge-sim view-episode --steps-per-day 20 --days 3 --narrative --recap --daily-log
```

Makefile convenience targets (pass extra flags via `ARGS`):

```bash
# Generate logs quickly (no DB)
make run

# Episode viewer
make run-episode
make run-episode ARGS="--narrative --recap --daily-log"

# Day viewer
make run-day ARGS="--day-index 1 --steps-per-day 25"

# Dedicated recap shortcut
make run-recap
```

### Agent explainer (deterministic, pre‑LLM)

Explain one agent’s arc using telemetry-only rules and character flavor:

```bash
uv run loopforge-sim explain-episode --steps-per-day 20 --days 3 --agent Delta
```

### LLM lens scaffolding (typed contracts + fake outputs)

Build/show the perception lens input and a deterministic “fake LLM” output for one agent on a day:

```bash
uv run loopforge-sim lens-agent --agent Delta --steps-per-day 20 --day-index 0
```

Types and helpers: `loopforge/llm_lens.py` (no external calls; safe for CI).

### Characters (style, not behavior)

A canonical character registry is available at `loopforge/characters.py` and the full lore in `docs/CHARACTER_BIBLE.md`. Reporting layers pull `visual`, `vibe`, and `tagline` from this registry to enrich character sheets and intros. Adding new agents? Give them an entry in `CHARACTERS` so they appear with personality.

### Logging paths and precedence (JSONL, fail‑soft)

- Action log path precedence: explicit `run_simulation(..., action_log_path=...)` > `ACTION_LOG_PATH` env var > default `logs/loopforge_actions.jsonl`.
- Supervisor log path precedence: `SUPERVISOR_LOG_PATH` env var > explicit `supervisor_log_path` param > default `logs/loopforge_supervisor.jsonl`.
- Readers are fail‑soft via `logging_utils.read_action_log_entries(path)` (malformed lines are skipped).

### Perception shaping (opt‑in)

- `PERCEPTION_MODE` env var: `accurate` (default), `partial`, `spin`.
- Helper `config.get_perception_mode()` normalizes unknown values back to `accurate`.
- Shaping is applied at the seam in `narrative.build_agent_perception(...)`; it only affects perception text fields, never core facts or numbers.

### CLI cheat sheet

```bash
# 1) Run a short sim (no DB)
uv run loopforge-sim --no-db --steps 60

# 2) Watch an episode from logs (add flags for narrative/recap/daily-log)
uv run loopforge-sim view-episode --steps-per-day 20 --days 3 --narrative --recap --daily-log

# 3) Explain one agent’s episode (deterministic)
uv run loopforge-sim explain-episode --steps-per-day 20 --days 3 --agent Delta

# 4) Future LLM lens scaffolding (typed input + deterministic fake output)
uv run loopforge-sim lens-agent --agent Delta --steps-per-day 20 --day-index 0
```

Notes:
- All narrative layers are pure, deterministic, and read‑only over logs.
- Numeric stats are telemetry‑only; reflections and text never change counts.
- See `docs/CINEMATIC_DEBUGGER.md` for a deeper “how to read it” guide.


---

## Supervisor Activity (daily scalar, deterministic)

A pure, telemetry‑derived scalar in [0,1] representing how often the Supervisor acted that day. Computed read‑only during analysis; it never changes simulation behavior.

- Definition: supervisor_activity = supervisor steps / steps_per_day (clamped 0..1)
- Where computed: `loopforge/supervisor_activity.py::compute_supervisor_activity(...)`
- Where used: threaded through CLI/analysis into `reporting.summarize_day(...)` to influence Attribution and Reflection (e.g., supervisor blame on rising stress).
- Docs: `docs/SUPERVISOR_ACTIVITY.md`

## Attribution Engine (read‑only, deterministic)

Per‑agent causal attribution for the day’s outcome, attached to each `DaySummary` as `belief_attributions[name]`.

- Function: `loopforge/attribution.py::derive_belief_attribution(...)`
- Inputs: guardrail/context counts, incidents, stress trend (vs previous day), supervisor_activity.
- Outputs: `cause` in {`self`,`supervisor`,`system`,`random`} + `confidence` (0..1).
- Surfaces: narrative closing line, daily log bullet (e.g., `- Attribution: system-driven (conf=0.70).`), recap arc (first → last).

## Narrative Consistency — Agent Reflection State (deterministic)

A lightweight state that keeps phrases consistent across days/logs, attached to `DaySummary` as `reflection_states[name]`.

- Type: `AgentReflectionState { stress_trend, rulebook_reliance, supervisor_presence }`
- Mapper: `loopforge/narrative_reflection.py::derive_reflection_state(...)` (EPS=0.01 trend bands; guardrail reliance ratio).
- Purpose: stabilize wording like “leans on protocol” and stress‑arc hints. Purely presentational; no behavior change.

## Emotional Arc Engine (EA‑1, deterministic)

**Emotional Arc Engine (EA-1, deterministic)**
A low-dimensional emotional snapshot per agent/day, attached to `DaySummary` as `emotion_states[name]`.

- **Type:** `AgentEmotionState { mood, certainty, energy }`  
- **Mapper:** `loopforge/emotion_model.py::derive_emotion_state(...)`  
- **Inputs:** stress bands + trend, attribution cause, previous day.  
- **Where it’s used now:**
  - **Day Narratives:** emotion-aware intros (“comes online steady but alert” vs “drifts into the shift almost relaxed”) and closings (“carrying some weight” vs “calm, nothing sticking”).
  - **Daily Logs:** a compact `Emotion: …` bullet per agent.
- **Scope:** pure, read-only; does not affect the sim loop or DB writes.

See `docs/EMOTIONAL_ARC_ENGINE.md` for rule details.

## Episode Analysis API + JSON Export (read‑only)

Programmatic API and CLI to compute multi‑day episode summaries and export a JSON representation with derived per‑agent blame timelines/counts.

- API: `loopforge/analysis_api.py::analyze_episode(action_log_path, supervisor_log_path=None, steps_per_day=50, days=3)` → `EpisodeSummary`
- Export helper: `episode_summary_to_dict(EpisodeSummary)` → JSON‑serializable dict including:
  - `days`: per-day basics (tension, incidents, per-agent guardrails/context/stress).
  - `agents`: per-agent episode aggregates (`guardrail_total`, `context_total`, `stress_start`/`stress_end`, etc.).
  - `tension_trend`: list of per-day tension scores.
  - `story_arc`: optional `EpisodeStoryArc` block (arc type, patterns, summary lines).
  - Per-agent:
    - `blame_timeline` + `blame_counts` (from the attribution engine),
    - `trait_snapshot` (episode-level drift snapshot).
  - `long_memory`: optional map of `name → AgentLongMemory` for slow character memory across episodes.

  All fields are additive; existing shapes remain backward-compatible.
- CLI:
  ```bash
  uv run loopforge-sim export-episode \
    --steps-per-day 20 \
    --days 3 \
    --output logs/episode_export.json
  ```

All of the above are deterministic, read‑only layers. They extend `DaySummary`/`EpisodeSummary` additively and never modify simulation behavior or JSONL log schemas.
