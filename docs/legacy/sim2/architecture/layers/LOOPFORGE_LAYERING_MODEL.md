# Loopforge Layering Model — Architect Onboarding Overview

_Version 1.0 — Written post-Migration Era_
_Architect: Gantry_

## Purpose of This Document

This overview defines the **canonical structure** of Loopforge after the first migration aka the Great Unflattenning of Nov 2025.  
It is written to give new Architects and Cartographers a **stable mental model,** prevent accidental regressions, and eliminate the historical confusion caused by flat modules, shim layers, and ambiguous import paths.

If you understand this document, you understand how the system fits together.

---

## 1. What Loopforge Is (Structurally)

Loopforge is a **layered simulation engine** composed of:
* **Core** — the simulation runtime (agents, environment, config)
* **Psych** — cognition, emotion, attribution, internal agent state
* **Narrative** — daily logs, episode recaps, story arcs, memory lines, explainer surfaces
* **Analytics** — summaries, registry, metrics, reporting, analysis API
* **LLM** — the policy seam and stub
* **DB** — persistence, models, migrations
* **Schema** — shared datatypes
* **CLI** — user-facing entrypoint
* **Root** — intentionally empty except for `__init__`

Historically, all modules lived beneath `loopforge/*.py`.
After the migration, **all real code lives inside these layered packages:**

```
loopforge/
  core/
  psych/
  narrative/
  analytics/
  llm/
  db/
  schema/
  cli/
  __init__.py
```

Every import in the system must now use **canonical layered paths,** never root aliases.

---

## 2. The Layer Purposes (Canonical Definitions)
### 2.1 Core Layer (`loopforge.core`)

The heart of the simulation.  
Contains:
* Simulation loop
* Agents (behavior shell)
* Environment
* Day runner
* Config, logging utilities, ID generators

**Key rule:**  
Core must not depend “upwards” on Narrative, Analytics, or UI.  
Circulars kill simulations.

---

### 2.2 Psych Layer (`loopforge.psych`)

Everything that makes an agent _a mind_:
* Emotion modeling
* Cognitive traits
* Attribution system
* Micro-incidents
* Supervisor biases + weather
* Internal supervisory messages
* Long-term memory

Psych sits **above Core,** but below Narrative and Analytics.

---

### 2.3 Narrative Layer (`loopforge.narrative`)

All storytelling and interpretive layers:
* Daily logs
* Episode recaps
* Story arc builder
* Memory lines
* Pressure notes
* Narrative viewer
* Explainer

Narrative transforms events into **interpretable explanations.**

---

### 2.4 Analytics Layer (`loopforge.analytics`)

All numerical and structural analysis:
* Day summaries
* Episode summaries
* Registry (Day/EpisodeRecord)
* Metrics and statistics
* Weave (snapshot extraction)
* Reflection engine (moved during final stage)

Analytics produces **structured outputs,** not prose.

---

### 2.5 LLM Layer (`loopforge.llm`)

The LLM policy seam lives here:
* LLM stub
* LLM client
* Policy routing logic (stub/real)

This keeps model-driven decisions isolated and testable.

---

### 2.6 DB Layer (`loopforge.db`)

Contains:
* SQLAlchemy models
* Memory store
* Alembic migrations
* Persistence helpers

The DB is intentionally **thin** and low-level.

### 2.7 Schema Layer (`loopforge.schema`)

Contains strongly-typed dataclasses:
* ActionLogEntry
* AgentReflection
* Episode/Tension/Snapshot
* All shared data types used across layers

This prevents circulars and allows upstream modules to share structured types.

---

### 2.8 CLI Layer (`loopforge.cli`)

User-facing entrypoint:
* Rich CLI built on Typer
* Exposes simulation runner, viewers, and analytics tools

Exports via:
```
python -m loopforge.cli.sim_cli
loopforge-sim
```

### 2.9 Root Package (`loopforge/*.py`) AFTER MIGRATION

Contains only:
```
__init__.py
```

Everything else has been **deleted or moved.**

---

## 3. Canonical Import Rules

These rules prevent deadlocks, ghost modules, and test failures.

### 3.1 Absolutely Forbidden

```python
from loopforge import emotions  # ❌
from loopforge import simulation  # ❌
from legacy.backend.loopforge_sim2 import narrative
import loopforge.models  # ❌
import loopforge.llm_stub  # ❌
```

These paths no longer exist.

### 3.2 Required Form

```python
from loopforge.core.simulation import

...
from loopforge.psych.emotions import

...
from legacy.backend.loopforge_sim2 import

...
from loopforge.analytics.reporting import

...
from legacy.backend.loopforge_sim2 import

...
from loopforge.db.models import

...
from loopforge.schema.types import

...
```

### 3.3 The Dependency Rules
* DB/Schema → must never depend on higher layers
* Core → may depend on: Schema, DB
* Psych → may depend on: Core, Schema
* LLM → may depend on: Core, Schema
* Narrative → may depend on: Core, Psych, Schema
* Analytics → may depend on: Core, Psych, Schema
* CLI → may depend on: Core, Narrative, Analytics, LLM, DB, Schema

**Topological rule:**
Lower layers must _never depend_ on higher layers.

## 4. Why Shims Existed (Historical Note)

The migration used temporary files like:
```
loopforge/emotions.py
loopforge/day_runner.py
loopforge/reporting.py
...
```

These were **shim modules:** thin re-export wrappers enabling tests and CLI to keep using old import paths during the migration.

As layers were moved, shims preserved:
* backwards compatibility
* monkeypatch targets
* import surface stability

Once every module and test was canonicalized, shims were removed.

#### Monkeypatching: Why the Sim Needed Stable Module Identity

Many tests monkeypatched behavior like:
```python
monkeypatch.setattr(loopforge.llm.llm_stub, "decide_robot_action_plan", fake_fn)
```

If early migration steps had pointed imports to _different module objects,_  
monkeypatching would patch one copy while the simulation used another.

This caused:
* non-deterministic test failures
* “this should be patched but isn’t” bugs
* import graph schizophrenia

Shims ensured **all callers referenced the same module object** until the migration was complete.

---

## 6. Post-Migration Guarantees

As of the completion of Gantry's sprints:
* Root directory is clean
* Imports are canonical
* All real logic lives in layered packages
* Shims are fully removed
* Tests and CLI run on a single import graph
* The LLM seam, registry, and narrative subsystems have stable boundaries
* Future changes will not resurrect duplicate modules

The system is now safe for:
* New Architects
* Multi-agent extensions
* New CLI tools
* Deeper DB integrations
* Automatic documentation generation
* Code intelligence & search tooling

---

## 7. Future Architect Instructions

When creating new modules:

### ✔ Put the file in the right layer
* If it’s agent state? → **psych**
* If it’s narrative or viewer logic? → **narrative**
* If it’s metrics, summaries, registry? → **analytics**
* If it’s runtime? → **core**
* If it’s policy/LLM? → **llm**

### ✔ Add new types to schema.types
Never to the root.

### ✔ Import only canonically
No shortcuts. No “quick fixes.”

### ✔ Maintain dependency direction
Lower → Higher is forbidden.

### ✔ Update tests accordingly
Tests must reference the same import surface the runtime uses.

The first migration is done, stability restored, shims purged. You may now resume breaking things responsibly.  
If anything collapses after this, it wasn’t the architecture. It was the operator.

— Gantry
Keeper of the Canonical Path