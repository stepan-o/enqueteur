Era II — Phase 3 Closure Report

Phase: 3 — Agent Identity & Expression Layer
Status: ✅ Complete
Date: 2025-11-26
Scope: ui-stage only (frontend). Backend / schema untouched.

1. Phase 3 Goal (Original Plan)

Sprint goal: Agents become characters.

Planned deliverables:

AgentCard v2 (avatar, vibe ring, stress glow, attribution cluster, tagline).

Integrate new identity into:

Episode Agents Overview.

Agent cameo slots inside DayStoryboard strips.

Belief–Attribution mini-panel:

Shows how the agent thought the day went.

Shows what actually happened.

Light delta indicator.

Target outcome:

“Agents have presence, personality, recognizable patterns — the cast is born.”

2. What Actually Shipped
   2.1 Agent Identity Model & Avatar v2

VM & tokens

Extended AgentViewModel with identity-focused fields:

vibeColorKey (maps to design tokens in tokens.css).

stressTier (low / mid / high).

displayTagline (human-readable role/summary line).

Centralized mapping from raw stage agent data → identity view model:

Deterministic tiering based on stress stats.

Safe fallbacks for missing or malformed fields.

AgentAvatar (v2)

New avatar component with:

Initial-based avatar shape.

Vibe ring using vibeColorKey.

Stress glow based on stressTier.

Size variants: sm, md, lg.

Accessible semantics:

Button/figure wrapper with clear label where needed.

No reliance on color alone for interactive affordances.

Legacy cleanup

AgentAvatarV1 was removed.

All avatar surfaces now use the unified AgentAvatar + AgentViewModel pipeline.

2.2 Episode Agents Overview — Identity Cards

Component: EpisodeAgentsOverview

Refactored from a plain list into identity cards:

Avatar v2 shown first for fast scanning.

Name + role grouped into a headline row.

Tagline row: displayTagline || tagline || "System agent".

Agents sorted by name for stable ordering.

A11y:

List semantics preserved.

Card content remains fully text-readable (no icon-only info).

Result: the overview now reads like a cast list rather than a stats table.

2.3 Episode Agents Panel — Upgraded to Identity v2

Component: EpisodeAgentsPanel

Still surfaces all existing metrics:

Average stress.

Guardrails and context totals.

Cause line.

Stress sparkline (unchanged behavior & tests).

Left-hand identity area now uses:

AgentAvatar v2.

Consistent identity styling with the overview.

Badges:

Guardrail (G:) and context (C:) badges kept for quick numeric read.

A11y:

Existing aria-labels for sparklines preserved.

Legacy text line retained for screen readers and tests.

Result: panel remains “metrics forward” but now visually anchors agents as characters.

2.4 Agent Cameos in DayStoryboard (Storyboard + Cast Integration)

VM: dayStoryboardVm

For each day we now derive:

agentCameos (up to 3 agents) with:

Name.

vibeColorKey.

stressTier.

agentCameoOverflowCount for display as +N when more agents are present.

Ordering:

Sorted by descending average stress, then name — the “most stressed voices” show up first.

Defensive behavior:

Missing data → skipped instead of crashing.

Empty results handled gracefully (no cameos rendered).

UI: DayStoryboardStrip

Each storyboard row shows a cameo cluster:

Up to 3 mini avatars (AgentAvatar v2 with size="sm").

Overflow pill (+N) with explanatory tooltip.

Interaction:

Cameos are keyboard-activable buttons with:

aria-label="View {agent}’s view of Day {N}".

Clicking a cameo:

Opens the belief mini-panel for that agent/day.

Does not change the selected day itself.

Clicking elsewhere on the strip:

Selects the day and scrolls the Day Detail into view (same behavior as Phase 2).

Result: each day strip now hints at which agents “own” that scene, without overwhelming the layout.

2.5 Belief–Attribution Mini-Panel

Component: AgentBeliefMiniPanel

Inline panel that appears under the storyboard when a cameo is selected.

Structure:

Title: “How {Agent} saw it”.

Belief text (cause or fallback):

e.g., random, system etc.

Tiny swap arrow indicator (for now symbolic, no extra logic).

“What actually happened” summary line:

Tension, incidents, supervisor activity, etc.

State wiring: LatestEpisodeView

Single piece of state: selectedBelief:

{ dayIndex, agentName } | null.

Behavior:

Click cameo → open (or toggle off if clicked again).

Changing selected day (timeline, row click, narrative selection) clears the belief panel.

Edge cases:

Null/missing belief → sensible fallback strings.

Changing episodes clears everything.

A11y

Panel is role="group" with descriptive heading.

Text content is fully accessible; no critical info hidden as icon-only.

Result: we now have a concrete UI surface for “how an agent saw the day” vs “what actually happened”, ready for richer overlays later.

3. Testing & Stability

Full ui-stage test suite passing.

New tests cover:

VM identity mapping, tier classification, cameo ordering, overflow.

AgentAvatar rendering and props.

EpisodeAgentsOverview and EpisodeAgentsPanel rendering and content expectations.

DayStoryboardStrip cameos (avatars, overflow, aria-labels, click behavior).

Belief mini-panel open/toggle/clear flows in LatestEpisodeView.

Backend:

No changes to StageEpisode, StageDay, or any API payload.

VM changes are strictly additive and backward-compatible.

4. How This Maps to the Original Phase 3 Goals

Goal: Agents become characters.

✅ AgentCard v2: Implemented via AgentAvatar + identity fields + refined overview/panel cards.

✅ Agent cameos in DayStoryboard: Shipped as mini avatars with stress-driven ordering and overflow handling.

✅ Belief–Attribution mini-panel: Implemented as AgentBeliefMiniPanel, toggled from cameos and showing “belief vs actual summary”.

Outcome vs spec:

Agents are now:

Visually distinct.

Consistently rendered across panels.

Connected to the storyboard (not just a separate stats table).

We intentionally did not:

Add per-cause icon badges or misalignment indicators yet — those are reserved as nice fits for Phase 5: Belief vs Truth Light Layer.

5. Known Non-Goals / Future Hooks

These are explicitly left for later eras or phases:

Cause-type iconography

Tiny icon / badge for belief cause (e.g. system vs random vs user).

Good candidate for Phase 5.

Quantitative belief-vs-truth overlays

Misalignment bars or divergence maps over cameos/strips.

Belongs in Era III cognition overlays.

Richer avatar art

Any move beyond flat 2D circles (illustrations, photos, etc.) is out of scope.

Current system is deliberately low-complexity and procedurally driven.

6. Ready State for Phase 4

From a system perspective, we’re ready to move into Phase 4 — Episode Story Mode because:

The cast is fully wired and visible across:

Top-level episode panels.

Day storyboard.

Belief mini-panel.

The day storyboard itself (Phase 2) is stable and now visually/semantically tied to agents.

Identity is centralized and VM-first, so Story Mode can:

Re-use avatars and agent summaries without new data contracts.

Chain storyboard strips and belief summaries into a vertical, story-like experience.

If we want a one-liner:

Phase 3 done: Episodes now have a cast you can recognize, follow, and listen to — the stage is ready for Story Mode.