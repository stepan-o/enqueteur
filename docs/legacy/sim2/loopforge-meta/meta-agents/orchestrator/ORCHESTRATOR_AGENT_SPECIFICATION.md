# Orchestrator Agent – Platform-Agnostic Specification (v0.1)

1. Orchestrator Responsibilities (single source of truth)

Think of the orchestrator as a pure “pipeline runner” with no clever AI logic:
**1. Resolve repo source**
* Local: use `repo_path` directly.
* GitHub: clone `<owner>/<repo>@ref` into a temp dir (using `git` CLI or `GitPython`).
**2. Scan & summarize code**
* Walk the repo.
* Select relevant files (e.g., `loopforge/**/*.py`, `scripts/*.py`).
* For each file, produce a **compact summary:**
  * `path`
  * `language` (e.g., `"python"`)
  * `size_bytes`
  * `top_level_defs`: list of `{type: "class"|"function", name: str}`
  * `imports`: simple list of imported module names
  * `docstring`: module-level docstring if present (shortened)
**3. Build Snapshotter prompt**
* System prompt: your Snapshotter instructions.
* User content: JSON of the file summaries + any contextual notes (e.g., repo name, commit hash).
**4. Call LLM (Snapshotter)**
* Use your `LLMClient` in JSON mode.
* Enforce schema: `ARCHITECTURE_SUMMARY_SNAPSHOT = {...}`.
**4. Validate & write snapshot**
* Ensure `ARCHITECTURE_SUMMARY_SNAPSHOT` exists and has `modules` list.
* Write to `docs/architecture/architecture_snapshots/ARCH_SUMMARY_SNAPSHOT_<timestamp>.json`.
**5. Log + exit**
* Print where the snapshot was written.
* Optionally, dump a .log / .meta.json with repo info & model used.

---

## 2. Data Contract: Orchestrator ↔ Snapshotter

### Input to Snapshotter (from Orchestrator):

```json
{
  "repo": {
    "name": "loopforge",
    "source": "local | github",
    "root_path": "loopforge/",
    "git": {
      "remote": "https://github.com/<owner>/<repo>.git",
    "ref": "main",
    "commit": "abc123..."
    }
  },
  "files": [
    {
      "path": "loopforge/core/simulation.py",
      "language": "python",
      "size_bytes": 8123,
      "imports": [
        "loopforge.core.environment",
        "loopforge.core.agents",
        "loopforge.llm.llm_stub"
      ],
      "top_level_defs": [
        {"type": "function", "name": "run_simulation"},
        {"type": "constant", "name": "INITIAL_ROBOTS"}
      ],
      "docstring": "Core simulation loop for Loopforge City..."
    }
    // ...
  ]
}
```

### Output from Snapshotter (to Orchestrator):

```json
{
  "ARCHITECTURE_SUMMARY_SNAPSHOT": {
  "generated_at": "2025-11-21T19:41:43Z",
  "modules": [ ... ],
  "uncertainties": [ ... ]
  }
}
```

Orchestrator does not interpret this — it just validates structure and writes it.