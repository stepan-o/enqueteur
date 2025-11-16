Working With Junie

A field guide for future Loopforge architects

Junie is our repo-aware code assistant. She’s smart, fast, and absolutely willing to yeet confident nonsense into your codebase if you let her.

This doc is for future architects who will be using Junie to evolve Loopforge: what she’s good at, where she falls over, and the workflow we used to keep her useful instead of destructive.

0. How to Think About Junie

Treat Junie as:

A very fast, slightly hallucination-prone mid-level dev

Who:

Reads context quickly

Writes decent diffs

But lies confidently about wiring, call graphs, and “what’s already implemented” if you don’t pin her down.

If you assume she is always right, you will get:

Great-sounding architecture

Subtle bugs

And long evenings staring at CLI output muttering “why is everything random again”.

If you treat her as a junior teammate who must be verified you’ll be fine.

1. Typical Failure Modes We Hit
1.1. “It’s implemented” (when it isn’t)

Junie will happily say:

“DaySummary is already wired into the CLI with previous_day_stats…”

…when in reality:

summarize_day(...) can accept previous_day_stats

But the CLI path (view_episode → compute_day_summary) never passed it, so the feature silently did nothing.

Pattern:
She infers the “intended” architecture and describes that, not the actual one.

Mitigation: Always ask her to show the exact file + function + code snippet in the repo, then verify.

1.2. Confusing “design” with “call chain”

She’s good at talking about:

“We’ll have a pure attribution engine, above the seam, read-only…”

But weaker at:

“What actually calls this, with which arguments, in the real CLI path?”

Example we hit:

BeliefAttribution logic was correct.

But the CLI path never threaded previous_day_stats, so every day looked like Day 0 → trend = unknown → cause = “random”.

The bug wasn’t in the algorithm; it was in “we forgot to wire the plumbing”.

Mitigation: Before accepting her changes, always ask:

“Walk me from uv run loopforge-sim view-episode ... down to the function that uses this new thing. Name each file and function in order.”

Then check that chain against the actual code.

1.3. Confident repo hallucinations

Junie sometimes:

Mentions files that don’t exist.

References functions using old signatures.

Assumes certain helpers are “already there” (clamp helpers, JSON helpers, etc.) when they are not.

Mitigation:

When you see a new file or helper mentioned, ask:
“Quote the existing definition of X from the repo”.
If she can’t show it, it doesn’t exist yet.

2. How to Use Junie Safely (The Workflow)
2.1. Start with a tight spec and hard constraints

For each sprint/change, spell out:

What’s allowed:

Deterministic only

No LLM / no randomness

Read-only; no simulation behavior changes

Additive fields only; no log schema breakage

What success looks like:

e.g.

“Day 0: random; later days: system when stress falls + guardrail-heavy; recap shows random → system.”

Make her repeat / restate the rules in her own words once.
This forces the constraints into her “working set”.

2.2. Make her propose a plan before touching code

Ask for something like:

“Give me a sprint plan: files, functions, and tests you’ll add/change. Keep it additive and deterministic.”

You want:

File list

Function names

What’s computed where

Which tests will assert the behavior

Only once the plan is coherent, ask for diffs.

2.3. Always demand concrete repo paths and snippets

Whenever she says “it’s wired”:

Ask:

“Which file and function contain that logic? Show me the exact code block.”

You (human) verify:

Does that file exist?

Does that function actually call what she claims?

Are the parameters what she says?

If not, you’ve just caught a hallucination early instead of debugging it via CLI later.

2.4. Keep changes small & layered

What worked well:

Sprint 2A: Add data model + pure attribution engine.

Sprint 2B: Minimal wiring to views.

Sprint 2C: Fix logic (trend bands, random spam) + tests.

Then: wire CLI threading for previous_day_stats.

Then: add reflection layer as a separate sprint.

Don’t let her mix:

New types

Logic

CLI wiring

And docs

…all in one massive, unreviewable blob. Split into small, reviewable steps.

2.5. Use tests to lock intent, not to discover it after the fact

For new logic (e.g. derive_belief_attribution):

Make Junie write explicit tests that encode the rules you care about:

incident + context-heavy → self

falling + guardrail-heavy → system

flat + no incidents → random, 0.20

Keep tests:

Deterministic

Using synthetic stats objects (no full sim needed)

This gives you a contract that you can quickly verify with pytest -q before touching the CLI or narrative layers.

2.6. Always run a human-readable scenario

Even if tests pass, still:

Run a short episode via CLI, like:

uv run loopforge-sim view-episode \
  --steps-per-day 20 \
  --days 3 \
  --narrative \
  --daily-log \
  --recap


Then sanity-scan:

Does Day 0 really say “random chance”?

Do later days switch to “the system” when stress clearly drops?

Does the recap pattern (“random → system”) match your mental model?

If the story feels wrong, assume wiring or edge-case logic is off, even if tests are green.

3. Prompt Patterns That Work Well
3.1. “You are a code reviewer, not a storyteller”

When things get slippery, switch Junie to a review mode:

“You are now acting purely as a Loopforge code reviewer. No new features. Read the snippets I paste and tell me:

What they actually do,

Where the wiring might be missing,

What minimal change is needed.”

This reduces her urge to invent entire subsystems.

3.2. Ask for “what changed” summaries

After she gives diffs, ask:

“Summarize what you actually changed:

Types

Logic

Call paths

Tests
in 8–10 bullets.”

Compare that summary to what you wanted.
If something feels off (e.g. “modified log schema” when you said “additive only”), stop there.

3.3. Force alignment with concrete symptoms

When debugging:

Paste the CLI output that looks wrong.

Then ask:

“Given this output and the rules we defined, what’s inconsistent? Which function could be responsible, and why? Name files and functions.”

This grounds her reasoning in actual runtime behavior instead of pure speculation.

4. Red Flags = Stop and Inspect

If you see Junie doing any of this, pause and inspect carefully:

Talking about modules or types that don’t exist.

Claiming features are “already wired” without showing call sites.

Changing simulation behavior or log schemas when you explicitly said “read-only, additive”.

Refusing (implicitly) to quote actual code when asked; responding only with “pseudo-diffs”.

Rule of thumb: if she can’t show you the code as it exists right now, don’t trust her description.

5. Quick Checklist for Future Architects

Before merging anything Junie helps with:

Spec checked

Constraints stated: deterministic, read-only, additive.

Desired behavior written down in human language.

Plan inspected

Files/functions listed.

Tests described.

Call path from CLI → new logic is named explicitly.

Code verified

For each “this already exists”, you’ve seen the actual snippet.

Diffs only touch the files you agreed on.

Tests

New tests exist for the new rules.

pytest -q is green.

Sanity run

loopforge-sim view-episode ... run with a small episode.

Output narrative matches the spec (e.g., random on Day 0, system later, etc.).

If any of these fail, Junie is not “bad” — she just needs another round of clarified prompts and tighter constraints.

TL;DR:
Junie is powerful, but you are still the architect. Use her like a sharp tool: with a spec, with tests, and with your eyes open.