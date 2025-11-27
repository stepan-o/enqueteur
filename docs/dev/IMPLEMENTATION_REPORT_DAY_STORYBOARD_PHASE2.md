# Day Storyboard — Phase 2 Polish (Sprint 2D) — Implementation Notes

Date: 2025-11-26 06:41 local
Author: Junie
Scope: ui-stage only. No backend/API/schema changes. VM changes remain additive and backward-compatible.

## Summary
- Applied a small visual polish pass to DayStoryboard strips (spacing, type hierarchy, subtle selected state) without changing semantics.
- Kept existing behaviors from 2A–2C: narrative lane rendering, tension band classes, tiny sparkline, and scroll/selection sync with Timeline + DayDetail.
- Added these developer notes to document tension/sparkline derivation and scroll-sync behavior for future maintainers.

## VM Data (high level)
Source: ui-stage/src/vm/dayStoryboardVm.ts

- tensionBandClass: classifies each day into one of "tensionLow" | "tensionMedium" | "tensionHigh" using day.tensionScore.
  - Thresholds (based on average tension):
    - avg < 0.25 → tensionLow
    - avg < 0.55 → tensionMedium
    - else       → tensionHigh
  - Missing/invalid tension defaults to Low for a safe neutral.
- sparklinePoints: normalized [0..1] sequence representing the intra-day trend proxy.
  - Current heuristic uses [prevDay.tensionScore, currentDay.tensionScore].
  - If data missing/flat, returns [].
- narrativeLane: minimal narrative items for the day; invalid blocks (missing id/kind/text) are dropped.
- caption: prefers the first narrative text from DayDetail; falls back to "No major events logged." for deterministic messaging.

All fields above are additive and optional in the VM; no renames or removals from previous phases.

## UI & A11y
- DayStoryboardStrip
  - Root button includes data-selected and aria-selected to reflect selection.
  - Applies a subtle background/border when selected.
  - Sparkline wrapper is role="img" with an aria-label summarizing trend: "Tension trend for Day N: rising|easing|fluctuating|steady".
  - Narrative lane items render as small pills, with data-selected and a clear focus/hover affordance.
- DayStoryboardList
  - Vertical list with consistent spacing; semantic roles: role="list" and child wrappers role="listitem".
  - Header "Storyboard" remains simple and non-distracting.

## Scroll Sync (Phase 2C recap)
- Single source of truth: selectedDayIndex lives in LatestEpisodeView.
- DayStoryboardList keeps a ref to the scroll container and to each strip wrapper.
- On scroll (rAF-throttled):
  - Computes which strip is visually dominant by comparing each strip center to the container center (closest wins).
  - If different from current selection, calls onSelectDay with that index.
- When selectedDayIndex changes (via storyboard, timeline, or narrative item click):
  - The selected strip scrolls into view inside the storyboard container.
  - LatestEpisodeView also gently scrolls the DayDetail panel into view (guarded under tests).
- A small token prop (scrollToSelectedDayToken) forces scrollIntoView even if the selected index hasn’t changed (e.g., repeated timeline clicks).

## Styling constraints
- Colors follow existing soft/neutrals; tension bands are mild so narrative text stays legible.
- Layout remains a single-row feeling: day chip → caption → narrative lane → sparkline.
- On narrow widths, elements wrap gracefully without overlap.

## Tests
- VM tests ensure band classification, sparkline normalization, and defensive behavior.
- Component tests cover list rendering, selection attributes, narrative lane accessibility/interactions, and scroll sync.
- Route-level tests confirm Timeline ↔ Storyboard ↔ DayDetail selection stays in sync, including scrollIntoView.

## Stability
- Backend untouched; StageEpisode/EpisodeViewModel shapes unchanged.
- Existing behavior preserved; additions are visual polish and docs.

— Junie
