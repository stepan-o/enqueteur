### Phase 3C — Agent Cameos + Belief Mini-Panel

Scope: ui-stage only. No backend/API/schema changes.

What shipped
- VM: dayStoryboardVm now exposes optional agentCameos (max 3) per day and agentCameoOverflowCount.
  - Cameos derive from StageEpisode.day[day_index].agents and reuse AgentViewModel identity via buildAgentViews.
  - Deterministic ordering: sort by avg_stress desc, then name asc. Pick top 3; the rest go to overflow count.
  - vibeColorKey is taken from AgentViewModel; stressTier is simplified to low/mid/high for compact cameo cues.
  - hasAttribution is true when attribution_cause is a non-empty string for that day/agent.
- UI: DayStoryboardStrip renders a small cameo cluster between the caption and sparkline.
  - Uses AgentAvatar v2 (size="sm"), respects vibe colors and stress glow.
  - Overflow rendered as a neutral "+N" pill with title.
  - Each cameo is an accessible control (role="button") with aria-label: "View {agent}'s view of Day {N}".
  - Keyboard-activatable with Enter/Space.
- Mini-Panel: Added AgentBeliefMiniPanel as an inline region (role="group").
  - Title: "How {agent} saw it" and body: attribution_cause or fallback.
  - Divider glyph ⇄ and a "What actually happened" one-liner composed from Day VM (tension, incidents, supervisor).
  - Wired in LatestEpisodeView with local state selectedBelief { dayIndex, agentName }.
  - Clicking the same cameo toggles the panel; selecting a different day (timeline/storyboard/narrative) clears it.

Derivation notes
- Cameos pull identity (vibeColorKey, stressTier) through buildAgentViews to ensure consistency with Agents Overview/Panel.
- stressTier is mapped to cameo tiers: none→low, cooldown/medium→mid, high→high.
- If any raw structures are malformed, agentCameos is [] and rendering skips without errors.

Out-of-scope (kept for later)
- Belief attribution icon cluster, animations, and richer misalignment metrics.
- Global heatmaps or timeline badges.

Tests added
- VM: cameo presence/length cap, overflow count, stable ordering, and tier mapping (DayStoryboardVm.test.ts).
- UI: DayStoryboardStrip cameo cluster rendering, overflow, aria-labels, and click plumbing.
- Mini-Panel: component renders belief and fallback; integration test in LatestEpisodeView verifies open/close and clear on day change.

Stability
- Purely additive VM fields; existing DayStoryboard behavior remains intact when no agent data available.
- No backend or schema changes.
