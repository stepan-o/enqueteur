# 🧭 Debugging the Loopforge Cartographer

Cartographer is a **non-interactive, extraction-only agent** whose entire job is to:

Read the repo using Extract Data

Produce an ARCHITECTURE_SUMMARY_SNAPSHOT

Optionally compare it to a previous snapshot and produce a DRIFT_REPORT

When it “fails”, it’s almost never logic inside Cartographer itself — it’s almost always:

bad Extract Data configuration,

misaligned schemas, or

the agent not being given the previous snapshot content in a usable form.

This doc is a small playbook to debug that.

0. Quick mental model

Cartographer:

Does not directly read files.

Only sees what Extract Data returns.

Must produce strictly structured JSON:

ARCHITECTURE_SUMMARY_SNAPSHOT = { ... }

DRIFT_REPORT = { ... } (if previous summary exists)

If Extract Data is wrong, Cartographer is operating blind.

1. First check: Is Extract Data returning what we think?
1.1. Confirm the schema

Current Extract Data schema (for the path/content variant):

{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "File path in the repository"
    },
    "content": {
      "type": "string",
      "description": "Raw file contents"
    }
  },
  "required": ["path", "content"]
}


Implications:

For each document scanned, Cartographer must emit a path and a content value.

If multiple files are scanned (e.g. 166 docs), the model must decide what to put in content for each of them.

If you see "content": "UNKNOWN" or empty strings across the board, the problem is almost always the instructions to Extract Data, not Cartographer.

2. Debugging “previous snapshot not found / UNKNOWN content”
Symptom

Cartographer says it’s using a previous snapshot at
docs/architecture/architecture_snapshots/ARCH_SUMMARY_SNAPSHOT_2025-11-19_BEFORE_MOVING_BOXES.json

But Extract Data results show content: "UNKNOWN" (or similar) for that file.

Root cause

The Extract Data query is vague. You’re asking it to:

retrieve the previous architecture summary from file X

…while also scanning many other documents with the same schema. The model doesn’t know:

whether to fill content only for that one file,

or how to behave for every other file,
so it often falls back to UNKNOWN everywhere.

Fix: make the instruction embarrassingly explicit

Use something like this as the Extract Data “query” text:

You are filling this schema for EACH document you see:

- "path": MUST ALWAYS be the full repository path of the current document.
- "content": we ONLY care about the previous architecture snapshot file.

Rules:

1. For every document:
   - Set "path" to the document's full repository path
     (e.g. "docs/architecture/.../file.json").

2. For "content":
   - If and only if the document path EXACTLY matches:
     "docs/architecture/architecture_snapshots/ARCH_SUMMARY_SNAPSHOT_2025-11-19_BEFORE_MOVING_BOXES.json"
     then set "content" to the FULL textual contents of this file.
   - For ALL other documents, set "content" to the string "UNKNOWN".

Do NOT summarize the JSON. For the snapshot file, copy its raw contents into
"content" as-is. For all other files, use "UNKNOWN".


Then:

Re-run Extract Data.

Inspect the results:

There should be exactly one row where:

path matches the snapshot path, and

content contains the full previous JSON.

Cartographer can then:

identify that row,

parse content as the previous ARCHITECTURE_SUMMARY_SNAPSHOT, and

produce a proper DRIFT_REPORT.

3. Debugging “Cartographer output is malformed / not matching schema”
Symptom

The final output has extra prose around the JSON.

Keys don’t match the schema (e.g. missing modules, uncertainties, or missing_in_repo).

Downstream tools complain about validation.

Checklist

Check the system prompt
Make sure Cartographer’s system prompt still includes:

“No text before, after, or between the JSON blocks.”

The exact schema for both:

ARCHITECTURE_SUMMARY_SNAPSHOT

DRIFT_REPORT

Scan for extra commentary
If the output has natural language before/after the JSON, update the system prompt to emphasize:

“Your entire response MUST be a JSON object containing the keys:

ARCHITECTURE_SUMMARY_SNAPSHOT

DRIFT_REPORT
No other text is allowed.”

Check required fields
Make sure Cartographer always sets:

generated_at (valid ISO datetime)

modules (array, possibly empty, but present)

uncertainties (array, possibly empty, but present)

And in DRIFT_REPORT:

All top-level keys exist, even if arrays are empty:

missing_in_repo, new_in_repo, interface_changes,

suspicious_differences, clarifications_needed,

recommended_updates.

If needed, explicitly state in the system prompt:

“If any list would be empty, output it as an empty array (e.g. []). Never omit required fields.”

4. Debugging “Drift report is useless / not reflecting changes”
Symptom

Cartographer produces a DRIFT_REPORT, but it doesn’t mention obvious changes:

modules moved from root to layered packages,

files that clearly disappeared,

new modules under loopforge/core, loopforge/psych, etc.

Possible causes

Previous snapshot is missing or not parsed
See section 2. If the previous snapshot JSON never reached Cartographer (or is UNKNOWN), it has nothing to compare against.

Previous snapshot structure changed
If earlier snapshots didn’t follow the same schema, Cartographer may fail to align them.

Debug steps

Manually inspect the previous snapshot file

Confirm it’s valid JSON.

Confirm top-level structure matches the current schema:

ARCHITECTURE_SUMMARY_SNAPSHOT = { ... }

has modules etc.

Instruct Cartographer to treat content as raw JSON
Make sure your instructions say that the content of that path is:

“the RAW JSON for the previous ARCHITECTURE_SUMMARY_SNAPSHOT. Do not paraphrase; parse it directly.”

Check missing_in_repo and new_in_repo behavior
Cartographer should:

treat a module path seen only in previous snapshot as missing_in_repo,

treat a path seen only in current scan as new_in_repo.

If it still doesn’t, add a gentle reminder in the system prompt:

“When comparing previous vs current summaries, treat module path as the primary key when deciding what is new or missing.”

5. Debugging “Cartographer missed modules / directories”
Symptom

A module clearly exists in loopforge/ but is missing from modules[] in the summary.

Root causes

Extract Data didn’t scan that directory.

Or the Extract Data query for the scan phase is too restrictive (e.g. only matches *.md or docs/).

Checklist

Confirm scan scope
Make sure the Extract Data “scan the repo” step is configured to include:

loopforge/

relevant scripts/ or docs/ folders if you want them in the architecture summary.

Look at the raw Extract Data output

Did the missing module’s .py file appear at all?

If not, adjust the search/filter in Dust.

Remind Cartographer what to treat as modules
In the system prompt, you can add:

“Treat any .py file under loopforge/ as a potential module to list in modules[], except __init__.py and tests.”

6. Sanity checks after fixing things

After you change Extract Data instructions or system prompt:

Run a dry run with a tiny scope

Instead of scanning “166 documents over all time”, start with a very narrow query:

Only the previous snapshot file.

Only one or two core modules.

Confirm that:

path is correct,

content is correct for the snapshot,

ARCHITECTURE_SUMMARY_SNAPSHOT.modules at least lists those modules.

Then scale up to full-repo scan

Once the minimal case works, expand the Extract Data call to the entire repo.

7. Operational tips & conventions

To make Cartographer’s life (and your life) easier long-term:

Dual snapshots
For each architecture run, consider writing two files:

ARCH_SUMMARY_SNAPSHOT_YYYY-MM-DD.json (machine-structured)

ARCH_SUMMARY_SNAPSHOT_YYYY-MM-DD.md (human/LLM prose summary)

Stable schema
Don’t change the snapshot schema casually. If you must:

bump a version in the snapshot filename or inside ARCHITECTURE_SUMMARY_SNAPSHOT,

teach Cartographer how to recognize older versions and fill gaps in DRIFT_REPORT via uncertainties / clarifications_needed.

When in doubt, log uncertainty
Cartographer must never “guess” which side is correct. If something looks off:

add an entry in uncertainties[] or clarifications_needed[] instead of rewriting reality.

8. Minimal debugging checklist

When Cartographer misbehaves, run through this:

Does Extract Data actually return the previous snapshot content?

One row where path == snapshot_path and content is full JSON.

Does Cartographer’s output match the schemas exactly?

No extra prose, all required keys present.

Does DRIFT_REPORT mention obviously missing/new modules?

If not, verify the previous snapshot JSON and path key logic.

Does Extract Data scan the files you expect?

If a module’s file never appears in Extract results, Cartographer can’t see it.

Once those four are green, Cartographer stops stumbling over itself and goes back to doing what it does best: quietly judging the architecture.

– Gantry