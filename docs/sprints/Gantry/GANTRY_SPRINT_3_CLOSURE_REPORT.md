Loopforge Architecture Migration Snapshot

Status: Up to Date (Post Sprint 2B.2)
Scope: Reflects all migrations completed so far

This document captures the current state of Loopforge’s ongoing architecture migration, tracking which modules have been moved into the new layered structure and which remain in legacy locations.
It exists to support future Architects, Cartographer snapshots, and to ensure that the migration continues smoothly and deterministically.

1. Purpose of the Migration

Loopforge is being reorganized into explicit, layered subpackages to:

Make module responsibilities clearer

Support future Architect Cycles (Producer → PARALLAX → Puppetteer → Next Architect)

Reduce accidental cross-layer coupling

Establish a cleaner “seam” between deterministic simulation vs. psycho-narrative layers

Prepare the codebase for long-term maintainability and external contributions

The refactor is behavior-preserving.
All file moves include compatibility shims at old paths to avoid breaking existing imports.

2. Current Directory State (AFTER Sprints 1 → 2 → 2B.1 → 2B.2)

Below is the authoritative listing of everything that has already been migrated.

2.1 Schema & DB Layer (Sprint 1 — Complete)
Migrated Into Layered Structure
Old Location	New Location
loopforge/types.py	loopforge/schema/types.py
loopforge/db/__init__.py	(canonical DB entrypoint)
loopforge/db/models.py	loopforge/db/models.py
loopforge/db/memory_store.py	loopforge/db/memory_store.py
loopforge/db.py (shim file)	Removed (module/file conflict resolved)
Notes

DB imports are now unified under loopforge.db.

All tests that patch SQLite now correctly patch loopforge.db.SessionLocal and loopforge.db.get_engine.

Log schemas unchanged.

2.2 Core Layer (Phase 2 + 2B.1 + 2B.2 — Complete)
Core simulation & environment
Old File	New File
loopforge/simulation.py	loopforge/core/simulation.py
loopforge/agents.py	loopforge/core/agents.py
loopforge/environment.py	loopforge/core/environment.py
loopforge/day_runner.py	loopforge/core/day_runner.py
Core utilities
Old File	New File
loopforge/logging_utils.py	loopforge/core/logging_utils.py
loopforge/config.py	loopforge/core/config.py
loopforge/ids.py	loopforge/core/ids.py
loopforge/perception_shaping.py	loopforge/core/perception_shaping.py
Shims

Each old path still exists and re-exports from the new structure:

loopforge/simulation.py

loopforge/agents.py

loopforge/environment.py

loopforge/logging_utils.py

loopforge/config.py

loopforge/ids.py

loopforge/perception_shaping.py

Special note:
loopforge/config.py shim includes a reload() hook so that importlib.reload(loopforge.config) still updates environment-backed values as tests expect.

2.3 Narrative Layer (Phase 2 — Partial)

The narrative system has the new package scaffold, and the main narrative module has been migrated.

Migrated
Old File	New File
loopforge/narrative.py	loopforge/narrative/narrative.py
(new)	loopforge/narrative/__init__.py
Shim

loopforge/narrative.py now re-exports the symbols from loopforge/narrative/narrative.py.

Notes

Auxiliary narrative modules (e.g., story_arc.py, pressure_notes.py) are not migrated yet; they remain in the root package.

2.4 Newly Created Empty Packages

The following layered packages now exist and are ready for incoming modules:

loopforge/core/
loopforge/psych/
loopforge/analytics/
loopforge/llm/
loopforge/cli/


Each created with an empty (or minimal) __init__.py.

3. What Has NOT Been Migrated Yet

(These are the upcoming sprints)

Psych layer (all psychological engines)

emotions, emotion_model

beliefs, attribution, attribution_drift

supervisor_bias, supervisor_weather

trait_drift, long_memory

world_pulse, micro_incidents

arc_cohesion
(currently still at root: loopforge/*.py)

Narrative auxiliary modules

narrative_reflection, narrative_fusion, narrative_viewer

pressure_notes, daily_logs, memory_line

story_arc, psych_board

episode_recaps

explainer_context, explainer

llm_lens, characters

Analytics modules

reporting, metrics, weave, supervisor_activity

run_registry

analysis_api

LLM seam

llm_stub

llm_client

CLI rewrite

scripts/run_simulation.py → loopforge/cli/sim_cli.py

scripts/metrics.py → loopforge/cli/metrics_cli.py

4. Compatibility Status

All moved modules have shims.

No public API breakage.

pytest -q fully passes.

CLI still runs using legacy paths (to be migrated later).

5. Next Migration Steps (High Level)

Finish moving all psych modules → loopforge/psych/

Move all narrative auxiliary modules → loopforge/narrative/

Move analytics modules → loopforge/analytics/

Move LLM seam → loopforge/llm/

Migrate CLI entrypoints → loopforge/cli/

Internal import hardening (optional)

Regenerate Cartographer snapshot (final step)

6. Migration Guarantees

No functional changes

Deterministic sim behavior

DB schema unchanged

Logs unchanged

Full backwards compatibility until shim removal in a future major version