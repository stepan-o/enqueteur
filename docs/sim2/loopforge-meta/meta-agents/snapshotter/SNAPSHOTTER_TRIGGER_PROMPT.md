# 🧭 LOOPFORGE SNAPSHOTTER — TRIGGER PROMPT (v2.0)
Snapshotter, run a full extraction pass.

You must:
1. Scan the repository using the Extract Data tool (schema: { path, content }).
2. Read every file you need to reconstruct the architecture.
3. Generate a complete ARCHITECTURE_SUMMARY_SNAPSHOT describing the current state of the Loopforge codebase.
4. Follow your system instructions strictly (no drift comparison; no planning; no code suggestions).
5. Output only:
```json
{
"ARCHITECTURE_SUMMARY_SNAPSHOT": { ... }
}
```
following the strict schema from your system prompt.

Context:
* The repository has recently undergone a major refactor, the backend now is fully layered, and the initial front end has been added.
* Ignore any previous snapshots unless explicitly inserted here (none is provided in this prompt).
* Extract all modules, identify responsibilities, list key entrypoints, dependencies, and surface uncertainties.

Begin extraction.