# DayStoryboard Skeleton — Implementation Report (Era II · Sprint 2A)

Date: 2025-11-25 19:10 local
Author: Junie (Loopforge Implementation Engineer)
Scope: ui-stage only (no backend changes)

## Summary
- Implemented DayStoryboard skeleton and integrated it into LatestEpisodeView.
- Reused existing EpisodeViewModel and DayDetail builders; no API or schema changes.
- Selection is single-source-of-truth via LatestEpisodeView’s selectedDayIndex and remains in sync with DayDetail and TimelineStrip.
- Visuals are intentionally minimal: vertical list of day strips with a left “Day N” pill, middle caption, and right placeholder sparkline box.

## Why
We want every day to feel like a scene. The DayStoryboard provides a structural, readable overview that users can click to navigate days, preparing for richer visuals and trend sparkles in later sprints.

## What Changed (File-by-File)

### ViewModel
- ui-stage/src/vm/dayStoryboardVm.ts
  - Added DayStoryboardItemViewModel interface.
  - Added buildDayStoryboardItems(episode):
    - Defensive: returns [] for malformed input.
    - Uses buildDayDetail to grab the first narrative text as caption; falls back to “No major events logged.”
    - Carries through tensionScore, incident presence, supervisorActivity.
    - Ensures items are sorted by dayIndex.

### Components
- ui-stage/src/components/DayStoryboard/DayStoryboardStrip.tsx
  - Presentational button for a single day row; exposes data-selected for testing and selected styles.
- ui-stage/src/components/DayStoryboard/DayStoryboardStrip.module.css
  - Basic styles: subtle selected tint + left border, day pill, caption text, placeholder sparkline box.
- ui-stage/src/components/DayStoryboard/DayStoryboardList.tsx
  - Renders header + a vertical list of strips.
  - Null-render when items is empty/invalid (graceful failure).
- ui-stage/src/components/DayStoryboard/DayStoryboardList.module.css
  - Minimal layout spacing.

### Route Integration
- ui-stage/src/routes/LatestEpisodeView.tsx
  - Imports buildDayStoryboardItems and DayStoryboardList.
  - Introduces selectedDayIndex state as the single selection source shared with TimelineStrip and DayDetail.
  - Renders DayStoryboardList above Day Detail.
  - On strip click, updates selection and gently scrolls DayDetail into view.

## Behavioral Stability
- Backend untouched.
- API unchanged.
- StageEpisode/EpisodeViewModel types unchanged.
- TimelineStrip behavior unchanged and remains in sync with storyboard selection.
- Fail-soft behavior preserved: if VM building or lists are malformed, the storyboard simply does not render.

## Notes on Data & Captioning
- Caption prioritizes the first available narrative block text for the day from buildDayDetail.
- Fallback caption (“No major events logged.”) ensures consistent, neutral messaging.

## Known Limitations (by design for Sprint 2A)
- No real sparkline (placeholder box only).
- No TimelineStrip redesign; light coordination only.
- No banner/mood adjustments beyond existing EpisodeMoodBannerV1.
- Minimal interaction/animation (hover/active only).

## Next Steps (Phase 2B+ candidates)
- Replace placeholder sparkline with a tiny SVG line chart using tensionTrend/day-level stats.
- Visual/mood pass for stronger day differentiation (consistent with ArcMood model).
- Richer caption logic: incorporate day summaries and agent highlights.

## Test Plan (deferred note)
The sprint includes VM, component, and route tests for stability. Per the current task instruction, tests need not be addressed in this commit, and we will revisit any test adjustments next.

## Appendix: Integration Diagram
LatestEpisodeView
- EpisodeMoodBannerV1
- EpisodeHeader
- EpisodeNavigator
- DayStoryboardList (new)
- TimelineStrip
- DayDetailPanel (selection synced)
- EpisodeAgentsPanel
- EpisodeStoryPanel

— Junie