Loopforge (Remaining) Migration Sprint Plan

From Current Snapshot → Fully Layered Architecture

This document defines the remaining sprints required to complete the Loopforge architecture migration.
It follows the corrected current-state snapshot (post Sprints 1 → 2 → 2B.1 → 2B.2) and breaks the remaining work into deterministic, Builder-friendly sprint units for Junie.

Each sprint is behavior-preserving, uses git mv + shims, and includes test verification (pytest -q).

0. Current Completed Work (Baseline)
Already migrated (canonical under layered structure)

Schema (types)

DB layer (db, models, memory_store)

Core (simulation, agents, environment, day_runner)

Core utilities (logging_utils, config, ids, perception_shaping)

Narrative (entry module) — narrative.py → narrative/narrative.py

All shims added for backward-compatible imports

All tests passing.
No functional changes made.
Ready for remaining module migrations.

This sprint plan starts from here.

1. Remaining Migration — High-Level Map

Modules still in old loopforge/*.py location must be moved into:

Layer	Target Directory	Status
Psych engines	loopforge/psych/	NOT DONE
Narrative (aux)	loopforge/narrative/	PARTIAL
Analytics	loopforge/analytics/	NOT DONE
LLM seam	loopforge/llm/	NOT DONE
CLI surface	loopforge/cli/	NOT DONE

Because this is a large migration, we break it into small, safe sprint units.

2. Sprint Structure Principles

Every Junie sprint must:

Use only git mv + shims

Introduce no behavioral changes

Avoid import rewrites until the final pass

Leave all tests green

Commit under Commitizen with proper type: chore(refactor): …

Update migration docs after each sprint

3. Sprint Roadmap (Implementation-Ready)

Below is the official sequence of future sprints, each small enough for a single Junie run.

Sprint 3 — Psych Layer Migration (Part 1: Foundations)

Move foundational psych modules.

Move to loopforge/psych/:

emotions.py

emotion_model.py

beliefs.py

Add shims:

loopforge/emotions.py

loopforge/emotion_model.py

loopforge/beliefs.py

Verification:

pytest -q

sanity import checks for both old and new paths

Sprint 4 — Psych Layer Migration (Part 2: Attribution & Drift)

Move to loopforge/psych/:

attribution.py

attribution_drift.py

trait_drift.py

long_memory.py

Add shims for each file.
pytest -q

Sprint 5 — Psych Layer Migration (Part 3: Supervisor Weather & Pulse)

Move to loopforge/psych/:

supervisor_bias.py

supervisor_weather.py

world_pulse.py

Add shims.
pytest -q

Sprint 6 — Psych Layer Migration (Part 4: Cohesion & Micro-Incidents)

Finalize psych layer.

Move to loopforge/psych/:

arc_cohesion.py

micro_incidents.py

Add shims.
pytest -q

At this point, all psych modules are layered.

Sprint 7 — Narrative Layer Migration (Part 1: Reflection + Fusion)

Move to loopforge/narrative/:

narrative_reflection.py

narrative_fusion.py

narrative_viewer.py

Add shims:

loopforge/narrative_reflection.py

loopforge/narrative_fusion.py

loopforge/narrative_viewer.py

Sprint 8 — Narrative Layer Migration (Part 2: Boards + Recaps)

Move to loopforge/narrative/:

story_arc.py

pressure_notes.py

memory_line.py

psych_board.py

daily_logs.py

episode_recaps.py

Add shims.
pytest -q

Narrative layer now complete.

Sprint 9 — Narrative Layer Migration (Part 3: Explainer / LLM-Lens)

Move to loopforge/narrative/:

explainer_context.py

explainer.py

llm_lens.py

characters.py

Add shims.

This finishes the narrative cluster.

Sprint 10 — Analytics Layer Migration (Part 1)

Move summary + reporting modules.

Move to loopforge/analytics/:

reporting.py

metrics.py

supervisor_activity.py

Add shims.

Sprint 11 — Analytics Layer Migration (Part 2)

Move to loopforge/analytics/:

weave.py

run_registry.py

analysis_api.py

Add shims.
pytest -q

Analytics layer now fully layered.

Sprint 12 — LLM Layer Migration

Move to loopforge/llm/:

llm_stub.py

llm_client.py

Add shims.
pytest -q

LLM seam layer complete.

Sprint 13 — CLI Migration (Part 1: sim_cli)

Move:

scripts/run_simulation.py → loopforge/cli/sim_cli.py

Update entrypoints in pyproject.toml
(but keep the legacy script callable).

Add shim file:

scripts/run_simulation.py (thin wrapper calling new CLI)

pytest + manual CLI smoke test

Sprint 14 — CLI Migration (Part 2: metrics_cli)

Move:

scripts/metrics.py → loopforge/cli/metrics_cli.py

Add shim script.

Update entrypoints.

Sprint 15 — Internal Import Hardening (Optional)

This sprint updates real imports to use:

from loopforge.core...
from loopforge.psych...
from loopforge.narrative...
from loopforge.analytics...
from loopforge.llm...


Shims remain for backward compatibility.

Sprint 16 — Cartographer Snapshot Regeneration

With the new structure complete:

Run Cartographer to produce new JSON architecture map

Generate new ARCHITECTURE_SUMMARY_SNAPSHOT.md

Regenerate dependency graphs

Produce updated Architect Onboarding Pack

4. End State

After Sprint 16, Loopforge will have:

A fully layered, explicit directory structure

No more root-level modules except shims

A stable API surface compliant with all Architect Cycle conventions

Clean future expansion paths for Producers, PARALLAX, Puppetteer, and future Architects

Ready for a major version bump when shims are eventually removed

5. Guarantees Throughout Migration

No functional behavior changes

No changes to DB schema or sim physics

No changes to JSONL log format

Full backwards compatibility preserved

All sprints gated by pytest -q

All moves done with git mv to preserve history