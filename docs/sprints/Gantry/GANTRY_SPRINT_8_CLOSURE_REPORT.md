1. Layer-by-layer snapshot
✅ Schema layer (loopforge.schema)

Status: Migrated & stable

Canonical: loopforge/schema/types.py

Old flat module: removed / shimmed as needed back in Sprint 1.

Everyone should think of loopforge.schema.types as the source of truth for datatypes.

✅ DB layer (loopforge.db)

Status: Migrated & stable

Canonical: loopforge/db/__init__.py, loopforge/db/models.py, loopforge/db/memory_store.py

Legacy loopforge/db.py shim was removed back in Sprint 1.

Simulation & tests now share one DB API: loopforge.db.

Architectically: DB is now a proper layer, not a random file.

✅ Core layer (loopforge.core)

Status: Migrated & shimmed

Canonical under loopforge.core:

simulation.py

agents.py

environment.py

day_runner.py

logging_utils.py

config.py

ids.py

perception_shaping.py

Legacy modules:

loopforge/simulation.py

loopforge/agents.py

loopforge/environment.py

loopforge/logging_utils.py

loopforge/config.py

loopforge/ids.py

loopforge/perception_shaping.py

All of those are full-parity shims that re-export everything from loopforge.core.*.
You’ve also got the special reload behavior handled for config.

So: core is functionally layered; legacy imports still work.

✅ Psych layer (loopforge.psych)

Status: Fully migrated & shimmed

Canonical under loopforge.psych:

Foundations:

emotions.py

emotion_model.py

beliefs.py

Higher-order:

attribution.py

attribution_drift.py

supervisor_bias.py

supervisor_weather.py

trait_drift.py

long_memory.py

world_pulse.py

micro_incidents.py (with the “always emit at least one soft incident for recaps” tweak)

arc_cohesion.py

Shims at top-level:

loopforge/emotions.py

loopforge/emotion_model.py

loopforge/beliefs.py

loopforge/attribution*.py, loopforge/supervisor_*.py, loopforge/trait_drift.py, loopforge/long_memory.py, loopforge/world_pulse.py, loopforge/micro_incidents.py, loopforge/arc_cohesion.py

All using the full-parity mirroring template (non-dunders mirrored, __all__ synced/synthesized). We also fixed the earlier _clamp-style parity bug pattern, so psych is clean.

✅ Narrative layer (loopforge.narrative)

Status: Fully migrated & shimmed

Canonical under loopforge.narrative:

Core:

narrative.py

narrative_reflection.py

narrative_fusion.py

Recaps & boards:

daily_logs.py

episode_recaps.py

psych_board.py

story_arc.py

Characters & pressure:

characters.py

pressure_notes.py

memory_line.py

Viewers & explainers:

narrative_viewer.py

explainer_context.py

explainer.py

llm_lens.py

Shims at top-level:

loopforge/narrative.py

loopforge/daily_logs.py

loopforge/episode_recaps.py

loopforge/psych_board.py

loopforge/story_arc.py

loopforge/narrative_reflection.py

loopforge/narrative_fusion.py

loopforge/characters.py

loopforge/narrative_viewer.py

loopforge/pressure_notes.py

loopforge/memory_line.py

loopforge/explainer_context.py

loopforge/explainer.py

loopforge/llm_lens.py

All with the standard full-parity shim pattern. Imports inside the canonical modules now mostly use:

loopforge.reporting → now loopforge.analytics.reporting

loopforge.schema.types

loopforge.psych.*

loopforge.narrative.characters, etc.

Narrative is now an honest-to-god layer, not a pile of flat files.

✅ Analytics layer (loopforge.analytics)

Status: Fully migrated & shimmed

Canonical under loopforge.analytics:

reporting.py

analysis_api.py

metrics.py

supervisor_activity.py

weave.py

run_registry.py

Shims at top-level:

loopforge/reporting.py

loopforge/analysis_api.py

loopforge/metrics.py

loopforge/supervisor_activity.py

loopforge/weave.py

loopforge/run_registry.py

Again: full-parity shims.

We also fixed:

view-episode --latest now respects registry_base / monkeypatched registry location and exits cleanly with a helpful message when no records exist.

Analytics is now properly layered and the “who owns run_registry?” story is at least consistent inside the analytics layer.

✅ CLI layer (loopforge.cli)

Status: Partially migrated (sim CLI done)

Canonical:

loopforge/cli/sim_cli.py — this now holds the Typer app that used to live in scripts/run_simulation.py.

Shim / wrapper:

scripts/run_simulation.py now imports loopforge.cli.sim_cli and:

Re-exports all non-dunder symbols.

Provides wrapper functions (view_episode, list_runs) that sync monkeypatched symbols (like summarize_episode, compute_day_summary) back into the canonical module — so tests that patch the old path still affect the real implementation.

CLI behavior is unchanged; you just quietly centralized the canonical implementation.

Other CLI surfaces (metrics, registry, weave) don’t exist yet as separate scripts, so there was nothing to migrate there.

🟡 LLM layer (loopforge.llm)

Status: Still pending migration / wiring

We’ve created the package (loopforge/llm/__init__.py), but we have not yet:

Moved llm_stub.py → loopforge/llm/llm_stub.py

Moved llm_client.py → loopforge/llm/llm_client.py

Added shims at loopforge/llm_stub.py and loopforge/llm_client.py

So the LLM seam is the main “big piece” still flat.

🟡 Global imports & shims

Status: Transitional but coherent

Right now:

Most new code in migrated modules imports via layered paths (loopforge.core.*, loopforge.schema.types, loopforge.psych.*, loopforge.narrative.*, loopforge.analytics.*).

A lot of older modules still rely on the old flat imports, now serviced by shims.

That’s fine for this stage of the migration. The long-term cleanup pass (post-migration) would:

Update remaining imports across the repo to hit layered canonical modules directly.

Optionally annotate shims with deprecation notes and plan for removal in a future major version.

2. What’s effectively “done”

You can think of the migration in terms of “how many floors are actually wired to the new panel”:

Core, Psych, Narrative, Analytics — ✅ fully migrated, canonicalized, and shimmed.

Schema + DB — ✅ were normalized in the very first sprint and are now stable.

CLI — ✅ sim CLI is layered; others are N/A for now (no legacy modules existed).

Shims — ✅ consistent pattern, strict symbol parity verified as you went.

From a contributor’s perspective:

New code should import from:

loopforge.core.*

loopforge.schema.types

loopforge.db

loopforge.psych.*

loopforge.narrative.*

loopforge.analytics.*

loopforge.cli.sim_cli

Old code still works via shims and tests are green.

You’re in that nice “dual-stack” phase: new architecture is real, but you haven’t broken anyone.

3. What’s clearly left (for future sprints)

If you want the quick todo list:

LLM layer migration

llm_stub.py & llm_client.py → loopforge/llm/* with shims.

Normalize imports from core/narrative/etc. into loopforge.llm.*.

Flat-module audit

Quick scan of loopforge/ root for any remaining “logic” modules that:

Should belong to core/psych/narrative/analytics/llm but are still flat.

Either migrate them or explicitly bless them as “top-level API only” with documentation.

Import normalization pass

Non-urgent, but eventually:

Replace from loopforge.reporting import ... with from loopforge.analytics.reporting import ..., etc., in whatever pockets still rely on shims.

After that, shims become truly legacy and can be scheduled for deprecation.

Run registry semantics (design-level, not just migration)

Decide:

Should the sim runner write EpisodeRecords at the end of a run?

Should view-episode stop appending to registry and only read?

Right now it works; the TODO is more about “source of truth hygiene” than correctness.