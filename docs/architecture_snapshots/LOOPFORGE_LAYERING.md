# LOOPFORGE LAYERING & ARCHITECT CYCLE SUPPORT

**Author:** Gantry (Meta-Architect)
**Version:** v1 – “Move the Boxes”

## 1. Why we’re doing this

Loopforge outgrew the “everything in `loopforge/`” flat layout.

We now have:
* Long-term Architect lineage (Lumen → Hinge → Producer → PARALLAX → Puppetteer → Next Architect).
* A Cartographer that can produce accurate architecture snapshots.
* Clear conceptual layering:
  * Core sim & infra
  * Above-the-seam psych engines
  * Narrative & boards
  * Analytics & tooling
  * LLM seam
  * CLI surface

But the code does not reflect those layers. That makes:
* Architect onboarding harder than it needs to be.
* refactors riskier (no clear “don’t touch this layer” boundaries).
* future contributions to our “multi-million-dollar open source project” more fragile than they should be.

This spec defines:
1. A **target subpackage structure** for Loopforge.
2. A **migration plan** for Junie (the builder agent).
3. Rules and conventions that support effective **Loopforge Architect Cycles.**

---

## 2. Core principles
These are the “building codes” I care about:
### 1. Layers must be explicit in both code and docs.  
Folder structure should reflect conceptual structure. No mystery “god packages”.
### 2. The seam is sacred.
* **Below the seam:** simulation mechanics, DB, environment.
* **Above the seam:** deterministic, log-powered psych & narrative.
* **Bridge:** modules that transform between them (perception → plan, LLM policy seam, orchestration).
### 3. Architects need a map, not a dump.
* Cartographer outputs a deep JSON snapshot.
* Architect onboarding needs a **short, human-readable entry path** built on top of that.
### 4. Minimal breakage in the short term.
* We prefer adding subpackages + compatibility shims over instantly breaking public imports.
* When we’re ready for a major version bump, we can remove shims.

---

## 3. Target package layout
### 3.1 High-level structure
New subpackages under `loopforge/`:
* `loopforge/core` – simulation & orchestration
* `loopforge/db` – persistence layer
* `loopforge/schema` – canonical datatypes (formerly `types.py`)
* `loopforge/psych` – psych engines (PARALLAX playground)
* `loopforge/narrative` – narrative & boards (Producer + Puppetteer playground)
* `loopforge/analytics` – metrics & episode summaries
* `loopforge/llm` – LLM seam (stub + client)
* `loopforge/cli` – CLI commands (sim + metrics)

### 3.2 File mapping (first pass)
core
loopforge/core/simulation.py ← loopforge/simulation.py
loopforge/core/agents.py ← loopforge/agents.py
loopforge/core/environment.py ← loopforge/environment.py
loopforge/core/day_runner.py ← loopforge/day_runner.py
loopforge/core/logging_utils.py ← loopforge/logging_utils.py
loopforge/core/config.py ← loopforge/config.py
loopforge/core/ids.py ← loopforge/ids.py

loopforge/core/perception_shaping.py ← loopforge/perception_shaping.py

db

loopforge/db/db.py ← loopforge/db.py

loopforge/db/models.py ← loopforge/models.py

loopforge/db/memory_store.py ← loopforge/memory_store.py

schema

loopforge/schema/types.py ← loopforge/types.py

psych

loopforge/psych/emotions.py ← loopforge/emotions.py

loopforge/psych/emotion_model.py ← loopforge/emotion_model.py

loopforge/psych/beliefs.py ← loopforge/beliefs.py

loopforge/psych/attribution.py ← loopforge/attribution.py

loopforge/psych/attribution_drift.py ← loopforge/attribution_drift.py

loopforge/psych/supervisor_bias.py ← loopforge/supervisor_bias.py

loopforge/psych/supervisor_weather.py ← loopforge/supervisor_weather.py

loopforge/psych/trait_drift.py ← loopforge/trait_drift.py

loopforge/psych/long_memory.py ← loopforge/long_memory.py

loopforge/psych/world_pulse.py ← loopforge/world_pulse.py

loopforge/psych/micro_incidents.py ← loopforge/micro_incidents.py

loopforge/psych/arc_cohesion.py ← loopforge/arc_cohesion.py

narrative

loopforge/narrative/narrative.py ← loopforge/narrative.py

loopforge/narrative/narrative_reflection.py ← loopforge/narrative_reflection.py

loopforge/narrative/narrative_fusion.py ← loopforge/narrative_fusion.py

loopforge/narrative/narrative_viewer.py ← loopforge/narrative_viewer.py

loopforge/narrative/pressure_notes.py ← loopforge/pressure_notes.py

loopforge/narrative/story_arc.py ← loopforge/story_arc.py

loopforge/narrative/daily_logs.py ← loopforge/daily_logs.py

loopforge/narrative/memory_line.py ← loopforge/memory_line.py

loopforge/narrative/episode_recaps.py ← loopforge/episode_recaps.py

loopforge/narrative/psych_board.py ← loopforge/psych_board.py

loopforge/narrative/explainer_context.py ← loopforge/explainer_context.py

loopforge/narrative/explainer.py ← loopforge/explainer.py

loopforge/narrative/llm_lens.py ← loopforge/llm_lens.py

loopforge/narrative/characters.py ← loopforge/characters.py

analytics

loopforge/analytics/reporting.py ← loopforge/reporting.py

loopforge/analytics/analysis_api.py ← loopforge/analysis_api.py

loopforge/analytics/metrics.py ← loopforge/metrics.py

loopforge/analytics/supervisor_activity.py ← loopforge/supervisor_activity.py

loopforge/analytics/weave.py ← loopforge/weave.py

loopforge/analytics/run_registry.py ← loopforge/run_registry.py

llm

loopforge/llm/llm_stub.py ← loopforge/llm_stub.py

loopforge/llm/llm_client.py ← loopforge/llm_client.py

cli

loopforge/cli/sim_cli.py ← scripts/run_simulation.py

loopforge/cli/metrics_cli.py ← scripts/metrics.py

Exact filenames for CLI can be tuned; the mapping is what matters.

4. Migration plan for Junie (“move the boxes, don’t break the building”)

Goal: Behavior-preserving refactor. No functional changes, only structure and imports.

Phase 1 – Create subpackages

For each of the target dirs above:

Create directory + __init__.py.

Ensure __all__ is either empty or minimal; we can control exports later.

Phase 2 – Move modules

Use git mv to move files according to the mapping in §3.2.

Recommended order to reduce import thrash:

schema, db

core

psych

narrative

analytics

llm

cli

Phase 3 – Fix imports

Update all internal imports to reflect the new structure.

Rules:

Replace old imports like:

from loopforge import simulation
from loopforge import emotions
from loopforge import reporting
from loopforge.types import AgentPerception


With:

from loopforge.core import simulation
from loopforge.psych import emotions
from loopforge.analytics import reporting
from loopforge.schema.types import AgentPerception


Prefer explicit subpackage imports over reaching through __init__ unless we intentionally design an API.

Phase 4 – Add compatibility shims (temporary)

To avoid immediately breaking external code / notebooks:

Leave thin modules at the old locations that re-export from the new structure, e.g.:

# loopforge/emotion_model.py
from loopforge.psych.emotion_model import *  # pragma: no cover

# loopforge/reporting.py
from loopforge.analytics.reporting import *  # pragma: no cover


Document that these are deprecated shims to be removed in a later major version.

Phase 5 – Wire CLI entry points to new loopforge/cli

Update pyproject.toml / setup.cfg entry points so that loopforge-sim and metrics commands point to loopforge.cli.sim_cli:main (or similar).

Keep backward-compatible function names (main, incidents, etc.) to minimize friction.

Phase 6 – Run tests & smoke checks

Run existing test suite (if present).

Manually run:

loopforge-sim basic run.

At least one analysis pipeline (export_episode, explain_episode, etc.).

Fix any missing imports / circular references that show up after the moves.

Phase 7 – Regenerate Cartographer snapshot

Once the structure is settled:

Run Cartographer again to produce a fresh ARCHITECTURE_SUMMARY_SNAPSHOT.

The new snapshot will:

Reflect the new paths.

Make the layered dependency graph obvious.

5. Layer & dependency rules (for future work)

These are the guardrails I’d like in place going forward.

5.1 Allowed directions

core can depend on:

schema

db

psych (limited: mostly for emotion hooks)

llm

psych can depend on:

schema

analytics (for summary types) read-only

narrative can depend on:

schema

analytics

psych

analytics can depend on:

schema

core only via logs & summaries, not DB or internals

db should not depend on:

core, psych, narrative, analytics, llm

llm:

llm_client depends on core.config, nothing else.

llm_stub depends on core, schema, psych, narrative as needed.

5.2 Anti-patterns (things to avoid)

db requiring psych or narrative → no feelings in the schema layer.

psych writing directly to the DB → must stay above the seam.

narrative calling simulation.run_simulation → narrative views should not trigger sim runs.

llm logic leaking into core/simulation.py → keep policy seam in llm_stub.

If a future Architect wants to cross a boundary, they need to:

Declare it explicitly in an architecture doc.

Justify why it’s not better modeled as an above-the-seam transformation.

6. Integrating this with Cartographer & snapshots

Once the new structure exists, we make Cartographer smarter with almost no extra work.

6.1 Infer layer from path

Cartographer can auto-tag:

loopforge/core/* → "layer": "core", "seam_zone": "below" | "bridge"

loopforge/db/* → "layer": "db", "seam_zone": "below"

loopforge/schema/* → "layer": "schema", "seam_zone": "bridge"

loopforge/psych/* → "layer": "psych", "seam_zone": "above"

loopforge/narrative/* → "layer": "narrative", "seam_zone": "above"

loopforge/analytics/* → "layer": "analytics", "seam_zone": "above"

loopforge/llm/* → "layer": "llm", "seam_zone": "bridge"

loopforge/cli/* → "layer": "cli", "seam_zone": "above"

No guessing from notes; the path is the contract.

6.2 Pipelines

Using the new structure, Cartographer can add named pipelines, e.g.:

core_simulation_pipeline

episode_analysis_pipeline

narrative_outputs_pipeline

Each is just an ordered list of {module, entrypoint} references. That becomes part of the Architect Onboarding Pack.

7. Making Architect Cycles effective

This layered structure is how we keep Architect personas from stepping on each other.

7.1 What each Architect should mainly touch

Hinge (historical)

loopforge/core, loopforge/db, loopforge/schema

Sim stability, logging, IDs, config.

Producer

loopforge/narrative, loopforge/analytics, loopforge/cli

Cinematic Debugger, recap flows, CLI tools.

PARALLAX

loopforge/psych, loopforge/analytics

Beliefs, traits, emotion arcs, long memory, attribution.

Puppetteer

loopforge/psych + loopforge/narrative fusion

Control surfaces that shape tension, pressure, supervisor weather, without touching DB or sim physics.

Next Architect

Cross-layer orchestration, new seam designs, API stabilization.

7.2 Architect Onboarding Pack (per cycle)

For each new Architect Cycle:

Cartographer snapshot – updated to new layout.

Layer map – short doc explaining:

What each subpackage is for.

Which ones are in-scope / out-of-scope for this Architect.

Pipelines overview – diagrams or bullet lists for:

sim → logs → summaries → narrative.

Open questions from uncertainties:

Tagged with suggested_owner = Producer / PARALLAX / Puppetteer / Next Architect.

You can think of it as:

“Here’s the building, here are the floors, here’s your floor, here are the known leaks.”

8. Non-goals for this spec

Just to be clear what we’re not doing in this pass:

No new features, no changes to sim behavior.

No redesign of narrative modules (we just move them; the overlap questions stay, but are now easier to address later).

No immediate API deprecation; shims keep old imports alive until you decide to cut a major version.