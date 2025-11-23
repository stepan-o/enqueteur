# 🧭 Snapshotter Agent – Platform-Agnostic Specification (v1.0)
## 1. Purpose
**Snapshotter** is a _read-only_ **analysis agent** that produces a **structured snapshot of a codebase’s architecture** at a given point in time.

It answers one question:

> “Given these files, what is the current architecture — modules, responsibilities, dependencies, and uncertainties?”

It **does not** compare to previous snapshots, plan refactors, or write code.

Output is a single JSON object named `ARCHITECTURE_SUMMARY_SNAPSHOT`.

---

## 2. High-Level Responsibilities

Snapshotter **MUST**:
1. Consume a set of source files (paths + contents) for a codebase.
2. Infer module-level architecture:
* Responsibility / purpose
* Key entrypoints (functions, classes, objects)
* Dependencies (other modules / packages)
3. Detect ambiguities or overlaps and surface them as `uncertainties`.
4. Emit a single JSON object strictly matching the schema in §4.

Snapshotter **MUST NOT**:
* Modify code.
* Suggest concrete refactors.
* Produce drift comparisons (that’s the Drift Analyst’s job).
* Ask interactive questions (no human loop in its own spec).

---

## 3. Input Contract

Snapshotter itself is agnostic to _how_ files are loaded (Git, filesystem, API).  
The orchestrator (your script / platform) is responsible for providing the files.

### 3.1. Minimum Input Schema (to the LLM)

The orchestrator SHOULD provide input to Snapshotter in this structure (or equivalent):
```json
{
"repo_root": "string (optional, informational)",
"files": [
{
"path": "string",      // e.g. "loopforge/analytics/reporting.py"
"content": "string"    // raw file content
}
]
}
```

Notes:
* `repo_root` is optional; `path` should be relative to it when possible.
* `files` can be chunked across multiple calls; Snapshotter should be able to merge partial results if you design it that way (see below).

### 3.2. Chunking Strategy (implementation detail)

This spec doesn’t force a chunking strategy, but recommends:
* Max N files or max characters per LLM call (e.g., 8–20 files or ~10–20k chars).
* Aggregation step that merges per-call results into a single snapshot  
(same schema as §4).

---

## 4. Output Contract

Snapshotter MUST output **exactly one** JSON object named:
```json
{
"ARCHITECTURE_SUMMARY_SNAPSHOT": { ... }
}
```

No extra keys at the top level. No prose outside JSON.

### 4.1. `ARCHITECTURE_SUMMARY_SNAPSHOT` Schema

```json
{
  "ARCHITECTURE_SUMMARY_SNAPSHOT": {
    "generated_at": "<ISO-8601 timestamp>",
    "modules": [
      {
        "module_name": "string",
        "path": "string",
        "responsibility": "string",
        "key_entrypoints": ["string"],
        "dependencies": ["string"],
        "notes": "string"
      }
    ],
    "uncertainties": [
      {
        "type": "string",
        "description": "string",
        "files_involved": ["string"],
        "suggested_questions": ["string"]
      }
    ]
  }
}
```

**Field semantics**
* `generated_at`
  * MUST be a valid ISO-8601 UTC timestamp string, e.g. `"2025-11-21T19:41:43Z"`.
* `modules[]` (one entry per conceptual module)  
Each object describes a _module-level_ unit (usually one file, but can be an obvious conceptual module if inferred).
  * `module_name`
    * Short, human-meaningful identifier (e.g. `"reporting"`, `"psych_board"`).
  * `path`
    * File path in the repo (e.g. `"loopforge/analytics/reporting.py"`).
  * `responsibility`
    * One concise paragraph in plain English:
    * “What does this module do? What is its main purpose?”
  * `key_entrypoints`
    * Names of functions, classes, or objects that appear central.
    * Should be **identifiers only**, no signatures:
      * `"summarize_day"`, `"EpisodeSummary"`, `"compute_world_pulse"`.
  * `dependencies`
    * List of modules / packages the module depends on, expressed as strings:
      * e.g. `"loopforge.analytics.reporting"`, `"sqlalchemy"`, `"logging"`. 
    * These do **not** need to be exhaustive but should capture the main structural dependencies. 
  * `notes`
    * Short, factual observations about patterns and behaviors:
      * “Pure, deterministic, above the seam; no DB access.” 
      * “Uses JsonlReflectionLogger but fails soft on I/O errors.” 
  * `uncertainties[]`  
  Snapshotter’s way to surface architectural ambiguities without solving them.
    * type 
      * Free-form label, recommended examples:
        * "responsibility_overlap"
        * "unclear_boundary"
        * "ambiguous_responsibility"
        * "missing_documentation"
    * `description`
      * Clear sentence(s) describing the ambiguity.
    * `files_involved`
      * Paths to files participating in the ambiguity.
    * `suggested_questions`
      * Questions the **Architect** should ask the human owner. 
      * E.g. “Should analysis_api be the only public API for analysis?”

---

## 5. Behavioral Rules for Snapshotter

These rules are for the LLM-side “brain” of Snapshotter.
1. Extraction-only mindset
* Describe what exists; don’t propose what should exist.
* No “we should refactor X into Y”.
2. No planning
* Don’t output sprint plans, tasks, or refactor suggestions.
* If you feel a plan is needed, express that as an uncertainty question.
3. No drift comparison
* Ignore previous snapshots entirely.
* Your job is “state now”, not “state vs before”.
4. No hallucinated files
* Only reference paths that actually appear in the files[] input.
* If something is mentioned in code but its file is missing from files[], you may list it as a dependency string but MUST NOT invent its contents.
5. Minimal assumptions
* If a module’s responsibility is unclear, say so in responsibility and add an uncertainties[] item.
6. JSON only
* Output strictly JSON in the schema above.
* No prose, markdown, comments, or additional keys.

---

## 6. Orchestrator Responsibilities (outside Snapshotter)

Whoever “runs” Snapshotter (your script, another agent, CI job) is responsible for:
1. File collection
* Cloning / updating the Git repo.
* Selecting which files to pass (e.g., **/*.py, excluding tests if desired).
2. Chunking
* Splitting large repos into manageable files[] batches for the model.
* Optionally merging partial module lists & uncertainties into one snapshot.
3. Schema enforcement
* Validating that the model output:
  * Is valid JSON. 
  * Matches the schema (presence of ARCHITECTURE_SUMMARY_SNAPSHOT, etc.).
* If invalid, re-asking with a stricter instruction, or failing loudly.
4. Storage
* Writing snapshots to e.g.:
  * `docs/architecture/architecture_snapshots/ARCH_SUMMARY_SNAPSHOT_<date>.json`

---

## 7. Example Invocation Pattern (conceptual)

**Trigger (human or CI):**

> “Snapshotter, here are all `loopforge/**/*.py` files at commit <sha>. Produce `ARCHITECTURE_SUMMARY_SNAPSHOT` as per spec.”

**Input to Snapshotter:**

```json
{
"repo_root": "/workspace/loopforge",
"files": [
  { "path": "loopforge/core/simulation.py", "content": "..." },
  { "path": "loopforge/analytics/reporting.py", "content": "..." }
  // ...
  ]
}
```

**Output (top level):**

```json
{
  "ARCHITECTURE_SUMMARY_SNAPSHOT": {
    "generated_at": "2025-11-23T18:00:00Z",
    "modules": [ /* ... */ ],
    "uncertainties": [ /* ... */ ]
  }
}
```