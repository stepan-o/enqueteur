# 🌙 LOOPFORGE — Shim Deprecation & Cleanup Roadmap
**(“The Great Unflattening — Final Phase”)**
## 🎯 Overall Goal

Finish the architecture migration by:
* Removing all top-level shim modules (simulation.py, agents.py, emotions.py, reporting.py, etc.)
* Updating every internal import to the layered canonical paths  
→ e.g., from loopforge.psych.beliefs import ...
* Ensuring the CLI entrypoints use only canonical modules
* Removing dead/duplicate files
* Regenerating Cartographer snapshot + architecture docs
* Confirming that tests + CLI remain green throughout the transition

This preserves the full layered structure, eliminates all transitional scaffolding, and ensures future work stays clean.

---

## 🧩 Sprint Structure Overview

To avoid breakage, we’ll remove shims in **safe, isolated slices,** starting with layers that **no other layers depend on.**

**Sprint order:**
1. Sprint A — Shim Discovery + Inventory Lock-In
2. Sprint B — Schema & DB Shim Removal
3. Sprint C — Core Shim Removal
4. Sprint D — Psych Shim Removal
5. Sprint E — Narrative Shim Removal
6. Sprint F — Analytics Shim Removal
7. Sprint G — LLM Shim Removal
8. Sprint H — CLI Shim Removal
9. Sprint I — Import Normalization (Repo-Wide)
10. Sprint J — Docs + Cartographer Snapshot Regeneration
11. Sprint K — Final Pass (Dead Files, Lint, Coverage)

Each sprint is safe, reversible, and independently testable.

---

## 🧪 Acceptance Criteria for Every Shim-Removal Sprint

Junie only finishes the sprint if all the following conditions are met:

### ✔ 1. shim module completely removed
(no file, no stub, no re-exports)

### ✔ 2. all imports updated
All repo references updated to canonical layered locations.

### ✔ 3. no import cycles created
Junie checks using:  
`python -m pip install flake8-import-order` (optional)  
or simply by running tests.

### ✔ 4. tests pass

`pytest -q` must be 100% green.

### ✔ 5. CLI works

`uv run python -m scripts.run_simulation --steps 3 --no-db`

### ✔ 6. REPL sanity

Both patterns must work:

```python
import loopforge.schema.types
from loopforge.schema.types import AgentPerception
```

No “legacy aliases” must exist.

---

## 🧩 Detailed Sprint Plan
### Sprint A — Shim Inventory Freeze (skipped)
> Sprint A was skipped, to energy consuming for Junie, somewhat redundant given that we've just completed initial refactoring.
**Goal:** Build a precise list of all existing shim modules + their canonical targets.

Tasks:
1. Search for all shim files matching known pattern:
* top-level python files that export from layered packages  
e.g., loopforge/simulation.py, loopforge/emotions.py, etc.

Produce a JSON or markdown inventory:
```json
{
  "shim": "loopforge/simulation.py",
  "canonical": "loopforge/core/simulation.py",
  "symbols": ["run_simulation", ...]
}
```

**Acceptance Criteria:**
* Inventory file generated
* No code changes
* Tests still green

We use this inventory to drive the removal sprints.

---

### Sprint B — Remove Schema + DB Shims

These are dependency roots → safest to do first.

**Tasks:**
* Remove:
  * `loopforge/types.py` shim
  * `loopforge/db.py` (should already be gone)
  * any leftover DB shim files
* Update all imports to:
  * `from loopforge.schema.types import ...`
  * `from loopforge.db import ...`

**Acceptance Criteria:**
* All tests green
* No code refers to legacy loopforge/types.py or loopforge/db.py

---

### Sprint C — Remove Core Shims

Shims to remove:
* `loopforge/simulation.py`
* `loopforge/environment.py`
* `loopforge/agents.py`
* `loopforge/day_runner.py`
* `loopforge/config.py` (shim version)
* `loopforge/logging_utils.py`
* `loopforge/perception_shaping.py`
* `loopforge/ids.py`

**Tasks:**
* Delete shim file
* Update imports to:
  * `loopforge.core.simulation`
  * `loopforge.core.environment`
  * etc.

**Acceptance Criteria:**
* All imports reference canonical paths
* Test suite green

---

### Sprint D — Remove Psych Shims

This layer is large; safe to remove now that Core is stable.

**Shims to remove:**
* `loopforge/emotions.py`
* `loopforge/emotion_model.py`
* `loopforge/beliefs.py`
* `loopforge/attribution.py`
* `loopforge/attribution_drift.py`
* `loopforge/supervisor_bias.py`
* `loopforge/supervisor_weather.py`
* `loopforge/trait_drift.py`
* `loopforge/long_memory.py`
* `loopforge/world_pulse.py`
* `loopforge/micro_incidents.py`
* `loopforge/arc_cohesion.py`

**Acceptance Criteria:**
* All internal imports corrected
* Tests green

---

### Sprint E — Remove Narrative Shims

Shims include:
* `daily_logs.py`
* `episode_recaps.py`
* `psych_board.py`
* `story_arc.py`
* `narrative_reflection.py`
* `narrative_fusion.py`
* `characters.py`
* `narrative_viewer.py`
* `memory_line.py`
* `pressure_notes.py`
* `explainer_context.py`
* `explainer.py`
* `llm_lens.py`

** Acceptance Criteria:** 
* No references to shim paths remain
* Recap & narrative tools still work
* Tests green

---

### Sprint F — Remove Analytics Shims

Shims include:
* `reporting.py`
* `analysis_api.py`
* `metrics.py`
* `supervisor_activity.py`
* `weave.py`
* `run_registry.py`

**Acceptance Criteria:**
* All imports refer to loopforge.analytics.*
* Registry tests still pass
* Tests green

---

### Sprint G — Remove LLM Shims

Shims:
* `loopforge/llm_stub.py`
* `loopforge/llm_client.py`

**Acceptance Criteria:**
* LLM stub tests (monkeypatch) still pass
* USE_LLM_POLICY branch still functions
* Tests green

---

### Sprint H — Remove CLI Shim

Delete:
* `scripts/run_simulation.py` shim
Update:
* Ensure entrypoints call `loopforge.cli.sim_cli:app`

Acceptance Criteria:
* running `python -m loopforge.cli.sim_cli` works
* `scripts/run_simulation.py` removed cleanly
* Tests green

---

### Sprint I — Repo-Wide Import Normalization
Junie scans all `.py` files and updates imports:
* Replace any `from loopforge.<module> import X` with canonical layered path:
* `loopforge.core.*`
* `loopforge.psych.*`
* `loopforge.narrative.*`
* `loopforge.analytics.*`
* `loopforge.llm.*`

**Acceptance Criteria:**
* No top-level imports referencing removed shims
* All imports canonical
* No circular imports
* Tests green

---

### Sprint J — Documentation Update
Tasks:
* Update:
  * README
  * ARCHITECTURE_EVOLUTION_PLAN
  * LOOPFORGE_AGENT_PROMPT.md
* Any developer docs
* Generate new Cartographer snapshot of the layered structure

**Acceptance Criteria:**
Docs match new structure
Snapshot present
No code changed

---

### Sprint K — Final Cleanup
**Tasks:**
* `git grep` for legacy modules – ensure total removal
* run:
```
ruff check --fix
black .
```
* optional: mypy pass
* Remove temp files, old comments, dead code

**Acceptance Criteria:**
* Repo fully normalized
* All tests green
* No shim files
* No references to top-level modules
* Architecture stable and clean

---

## 🎉 After These Sprints
Loopforge becomes:
* **Fully layered**
* **Shim-free**
* **Import-clean**
* **Cartographer-synced**
* **Ready for all future Architect Cycles**

Effectively: this completes “The Great Unflattening.”