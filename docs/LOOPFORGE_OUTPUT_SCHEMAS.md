# Schema 1 — ARCHITECTURE_SUMMARY

Used by: CARTOGRAPHER (provides briefs each eng cycle to LLM-Architect)
- Scan the entire repository using Extract Data.
- Parse code modules, directories, classes, functions, and responsibilities.
- Produce a structured, canonical ARCHITECTURE_SUMMARY.

{
  "generated_at": "2025-02-..",
  "modules": [
    {
      "module_name": "narrative",
      "path": "loopforge/narrative.py",
      "responsibility": "Defines perception→plan seam primitives",
      "key_entrypoints": ["AgentPerception", "AgentActionPlan", "..."],
      "dependencies": ["env", "config"],
      "notes": "Phase-1 primitives; reflection not implemented."
    }
  ]
}

# Schema 2 — DRIFT_REPORT

Used by: CARTOGRAPHER (provides briefs each eng cycle to LLM-Architect)
- When given a previous summary, compare and generate a DRIFT_REPORT.

{
  "missing_in_repo": [],
  "new_in_repo": [],
  "interface_changes": [],
  "suspicious_differences": [],
  "recommended_updates": "..."
}
