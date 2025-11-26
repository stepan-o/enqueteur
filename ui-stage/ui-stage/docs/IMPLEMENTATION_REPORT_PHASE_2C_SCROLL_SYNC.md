# Era II — Phase 2C: Hybrid Timeline + Storyboard & Scroll Sync — Implementation Report

Date: 2025-11-26 06:22 local
Author: Junie
Scope: ui-stage only (frontend). No backend/API/schema changes.

## Summary
- Implemented shared, scroll-aware navigation between DayStoryboard, Timeline, and DayDetail.
- DayStoryboardList now:
  - Auto-selects the visually dominant day on scroll (center-heuristic).
  - Scrolls the selected strip into view when selection changes (e.g., timeline click).
  - Exposes stable data/test attributes and accessibility states.
- LatestEpisodeView remains the single source of truth for `selectedDayIndex`.
- Added comprehensive tests for scroll sync and timeline↔storyboard interactions.
- All frontend tests pass (146/146), backend tests previously green and unchanged.

## What Changed

### Components
- ui-stage/src/components/DayStoryboard/DayStoryboardStrip.tsx
  - Add `aria-selected` to root button alongside existing `aria-pressed` and `data-selected`.

- ui-stage/src/components/DayStoryboard/DayStoryboardList.tsx
  - Introduced scroll container and per-strip refs to calculate dominant day on scroll.
  - rAF-throttled `onScroll` handler to avoid spamming updates.
  - New optional prop `scrollToSelectedDayToken` to force scroll into view even if the selected index is unchanged (used when timeline pill is clicked repeatedly).
  - Added container `data-testid="day-storyboard-container"`, `role="list"`, and each strip wrapper gets `data-day-index` and `role="listitem"` for semantic clarity/testing.

### Route Integration
- ui-stage/src/routes/LatestEpisodeView.tsx
  - Added `scrollStoryboardToken` state and passed it to DayStoryboardList.
  - On timeline `onSelect`, increment the token to ensure storyboard scrolls the corresponding strip into view.
  - Kept DayDetail scroll-into-view behavior after selection (guarded for jsdom).

### Tests
- ui-stage/src/components/DayStoryboard/DayStoryboardList.scrollSync.test.tsx (new)
  - Verifies scroll-based auto-selection by stubbing `getBoundingClientRect` and ensuring `onSelectDay` receives the dominant index.
  - Verifies that changing `selectedDayIndex` triggers `scrollIntoView` on the correct strip.
  - Stubs `requestAnimationFrame` for deterministic behavior under jsdom.

- ui-stage/src/routes/LatestEpisodeView.timelineStoryboardSync.test.tsx (new)
  - Scenario A: clicking a storyboard strip updates timeline selection and DayDetail header.
  - Scenario B: clicking a timeline pill applies selection to storyboard, calls `scrollIntoView` on the strip, and updates DayDetail.

- Existing tests remain unchanged and pass, confirming no regressions.

## Behavior & UX
- Single source of truth for day selection lives in LatestEpisodeView.
- Scrolling the storyboard updates selected day across storyboard, timeline, and detail.
- Clicking the timeline causes the storyboard to scroll the corresponding strip into view.
- Selected storyboard strips are visually and semantically distinct via `data-selected="true"` and `aria-selected="true"`.
- Scroll handler is throttled via `requestAnimationFrame` for performance and test determinism.

## Stability Guarantees
- Backend/API untouched.
- StageEpisode/EpisodeViewModel shapes unchanged.
- VM additions from earlier phases preserved; no breaking changes.

## Notes & Future Work (Phase 2D+)
- Consider debouncing scroll update if needed for extremely large episodes.
- Potentially align the center-heuristic with an explicit top threshold if users prefer “select the first fully visible” behavior.
- Expand the token mechanism to handle external programmatic jumps (e.g., deep links) if needed.

— Junie
