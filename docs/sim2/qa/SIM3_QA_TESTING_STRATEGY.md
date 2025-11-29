Sim3 is a simulation engine — which means:

the core state transitions must be stable

the policy layer (AI/LLM) must be mockable

the output schema must remain stable (StageEpisode v2)

the replay determinism must be guaranteed

To ensure this, you want three layers of QA:

🔹 Layer 1 — Lightweight unit tests (quick, local, fast)

Covers pure functions and deterministic logic.

Modules covered here:

Config

scenario_config.py

World

room loading

adjacency correctness

coordinate ranges

Cast

loading character presets

Time

tick ↔ day conversion

cycle reset boundaries

Engine helpers

basic scene extraction ordering

tension tier calculation

These tests run in <1 second and ensure nothing silly breaks.

🔹 Layer 2 — Mid-level “integration tests” (the real backbone)

These are the most important for Sim3.

You want tests that:

run a short deterministic scenario (e.g., 20 ticks, 1 day)

validate:

world loads correctly

cast is instantiated

engine completes a run

output is well-formed StageEpisodeV2 JSON

The key: Mock the LLM

We replace the AI with:

def fake_policy(perception):
return {"action": "idle"}


This makes the simulation fully deterministic and testable.

This ensures:

no nondeterministic LLM behavior

stable replay

schema consistency

API-level correctness

These tests catch ~70% of real bugs.

🔹 Layer 3 — High-level “schema snapshot tests”

This is the killer feature for Loopforge QA.

Snapshot tests:

Run a deterministic scenario

Build a StageEpisodeV2 object

Compare the JSON output to a frozen reference snapshot

Basically:

episode = build_stage_episode(...)
assert episode.to_dict() == load_snapshot("scenario_baseline.json")


When something changes:

If the new output is correct → manually approve an updated snapshot

If not → you catch a regression instantly

Why snapshot tests matter:

Because your frontend expects a stable schema.

Snapshots guarantee:

rooms appear in stable order

scenes appear in right structure

tension trends are array-aligned

character sheets are correct

no new fields missing or renamed

This is exactly how Storybook, Jest, and large simulation projects maintain schema stability.

🔹 Optional Layer 4 — “Replay consistency tests”

If you enable a persistent run log, you can do:

Run a scenario

Export episode JSON

Replay the episode

Compare summary results

This guarantees:

state transitions are reversible

logs are internally coherent

day boundaries are preserved

This is optional but useful for long-term engine stability once Sim3 matures.

🔥 3. What you do NOT need (to save time)

No tests for getters/setters

No tests for dataclasses beyond validation

No tests for UI formatting

No tests for complex agent logic yet

No tests for visual layout

These are slow and bring low ROI.

🧪 4. Recommendation: Folder structure for QA
tests/
sim3/
config/
test_scenario_config.py
test_world_registry.py
world/
test_world_model.py
agents/
test_agent_model.py
engine/
test_sim_loop_basic.py
test_scene_extractor.py
output/
test_stage_episode_schema.py
snapshots/
scenario_baseline.json
scenario_short.json


This structure gives:

fast feedback

clear areas of responsibility

safety around schema stability