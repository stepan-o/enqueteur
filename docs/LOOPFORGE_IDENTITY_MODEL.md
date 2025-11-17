# Loopforge Identity Model — Runs, Episodes & Events

> Draft design note for IDs, logging, and future DB schema.

## 1. Why this exists

Loopforge increasingly needs to:
* **Replay** and visualize past simulations.
* **Compare** episodes (A/B configs, different world pulses, etc.).
* **Trace** any artifact (action log line, viz, report) back to “which run, which episode?”.
* Eventually **persist** everything in a real DB, not just JSONL.

To do that cleanly, we standardize on **two core IDs**:
* `run_id` – identity of a full simulation job.
* `episode_id` – identity of one narrative episode within that run.

Everything else hangs off those two.

## 2. Identity model
### 2.1 Run
* run_id: generated once at the start of a CLI invocation (or orchestrated job).

Type: opaque string (UUID4 / short hash / deterministic seed-based, doesn’t matter as long as unique-enough).

Semantics: “This is that one time we hit view-episode (or a batch runner) with these parameters.”

Possible future fields (RunContext):

created_at

seed

scenario_name

config_version

2.2 Episode

Within a run:

episode_index: integer 0, 1, 2, ... scoped to that run.

episode_id: unique per episode, within the whole system, not just the run.

Suggested pattern (but not required):
episode_id = f"{run_id}-ep{episode_index}"

Today: one run = one episode (episode_index = 0).
Future: multi-episode runs without changing the identity model.

2.3 Agent events

Any event (action, reflection, supervisor move, etc.) must carry:

run_id

episode_index

(optionally) episode_id for convenience

That’s the core foreign key triple. Everything else (timestamps, step, agent name) is local context.

3. Where IDs live
3.1 In-memory structures

EpisodeSummary (already partially done; this just formalizes it):

@dataclass
class EpisodeSummary:
    run_id: Optional[str] = None
    episode_id: Optional[str] = None
    episode_index: int = 0

    # existing fields:
    days: list[DaySummary]
    agents: dict[str, AgentEpisodeStats]
    tension_trend: list[float]
    story_arc: Optional[StoryArc] = None
    world_pulse_history: Optional[list[dict]] = None
    # ... long_memory, etc.


DaySummary and AgentDayStats usually don’t need IDs themselves if they are always accessed via the EpisodeSummary. They’re logically “episode-scoped”.

3.2 JSONL logs

For each log line (examples: action logs, supervisor logs, reflections):

Minimal required core:

{
  "run_id": "run_2025-11-17T21-03-12Z_ab12cd",
  "episode_index": 0,
  "episode_id": "run_2025-11-17T21-03-12Z_ab12cd-ep0",
  "step": 37,
  "agent": "STILETTO-9",
  "action_type": "guardrail",
  "payload": { "...": "..." },
  "timestamp": "2025-11-17T21:03:45.123Z"
}


Same for supervisor events and reflections; their schemas differ, but the IDs are common.

This is what makes it trivial to:

Slice all events for a specific episode later.

Move from JSONL → DB with almost no redesign.

3.3 Episode registry (“catalog”)

A separate JSONL (later, DB table) that lists episodes and their metadata.

File: episode_registry.jsonl (or similar)

One line per episode:

{
  "run_id": "run_2025-11-17T21-03-12Z_ab12cd",
  "episode_id": "run_2025-11-17T21-03-12Z_ab12cd-ep0",
  "episode_index": 0,
  "created_at": "2025-11-17T21:03:12Z",

  "steps_per_day": 20,
  "days": 3,
  "seed": 1234,
  "scenario_name": "default_factory_smoke_test",

  "action_log_path": "logs/loopforge_actions.jsonl",
  "supervisor_log_path": "logs/loopforge_supervisor.jsonl",
  "reflection_log_path": "logs/loopforge_reflections.jsonl",

  "config_version": "v0.3.1",
  "notes": "Rust-Goth cast disabled; using Delta/Nova/Sprocket."
}


Later this becomes:

runs table (run-level info),

episodes table (episode-level info, foreign key to runs).

4. How IDs are generated and threaded

At start of view-episode run:

Generate run_id.

Set episode_index = 0 (for now).

Derive episode_id.

run_id = generate_run_id()  # uuid4+timestamp or similar
episode_index = 0
episode_id = f"{run_id}-ep{episode_index}"


Pass down to:

The simulation that writes action / supervisor / reflection logs:

Every log writer gets (run_id, episode_index, episode_id) and stamps it on each line.

compute_day_summary / summarize_episode:

summarize_episode(day_summaries, run_id=run_id, episode_id=episode_id, episode_index=episode_index)

EpisodeSummary:

Stores all three for later reporting and exports.

Registry writer:

After the episode is done, append a registry line with this ID triple + metadata.

This ensures:

Any action line → episode_registry → EpisodeSummary → recap → viz
all sit on the same IDs.

5. Where IDs will be used (now and later)

Let’s list the main consumers so we don’t forget anything.

5.1 Analysis API

analyze_episode(...) today:

Loads logs from path, computes day summaries, returns EpisodeSummary.

With IDs:

It can accept episode_id (or run_id + episode_index) instead of raw file paths:

Look up the episode in episode_registry.jsonl.

Grab the log paths + parameters.

Run the exact same compute pipeline.

This is the key to “replay any episode later” and for DB-backed viz.

5.2 Reporting / recaps / world pulse

All the nice things we’ve just added:

WORLD PULSE

ARC COHESION

MEMORY LINE

PRESSURE NOTES

PSYCH BOARD

PSYCH SNAPSHOT

All operate on EpisodeSummary. That summary now carries:

run_id, episode_id, episode_index

So:

UI tools can show “Episode XXX from Run YYY” on screen.

A future web viz can query by episode_id, fetch raw logs from DB, and cross-check against summary.

5.3 Future DB schema & viz

If/when you move to a database, a minimal design could look like:

runs

run_id (PK)

created_at

seed

scenario_name

config_version

meta (JSON)

episodes

episode_id (PK)

run_id (FK → runs)

episode_index

steps_per_day

days

summary_blob (optional full EpisodeSummary JSON)

created_at

agent_actions

id (PK)

run_id (FK)

episode_id (FK)

episode_index

step

agent_name

action_type

payload (JSON)

timestamp

supervisor_events, reflections, world_pulses, etc. all follow the same pattern: always have (run_id, episode_id, episode_index).

Result: your viz layer can literally be implemented against:

SELECT *
FROM agent_actions
WHERE episode_id = 'run_2025-...-ep0'
ORDER BY step;


…instead of touching JSONL at all.

5.4 Experiments / configs later

Once IDs exist everywhere, you can also:

Attach experiment labels to runs:

experiment_name, variant, config_hash.

Run A/B episodes and query:

“Show me all episodes in experiment perception_spin_v1 where STATIC_KID was present and tension escalated.”

Because everything is scoped by (run_id, episode_id), that’s a simple join, not archaeology.

6. What else should link to IDs?

To make the design fully future-proof, this is the checklist:

Must carry IDs now:

Action logs

Supervisor logs

Reflection logs

EpisodeSummary (run_id, episode_id, episode_index)

Episode registry entries

episode_summary_to_dict export (for external tools)

Good to attach soon-ish:

Any intermediate on-disk artifacts:

e.g., cached day summaries → include [run_id, episode_id, episode_index] in filenames or inside the JSON.

Visualization “snapshots” or exports:

If you ever dump a plot or HTML viz to disk, embed (run_id, episode_id) in filename and metadata:

runs/run_<id>/episode_<episode_index>/psych_board.png

Later, when DB arrives:

Every table that represents events or aggregates should have (run_id, episode_id, episode_index) as part of its key or foreign keys.

7. How to turn this into Junie work

You’re basically ready to tell Junie:

Confirm EpisodeSummary has run_id, episode_id, episode_index and they’re exported in episode_summary_to_dict.

Ensure the CLI creates run_id once, derives episode_id, sets episode_index, and:

passes them to the sim,

passes them to summarize_episode,

writes them on every JSONL line.

Add episode_registry.py with a simple JSONL append.

Extend analysis_api.analyze_episode to accept an episode_id and lookup via registry (optional,