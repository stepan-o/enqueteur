### Stage Map — Phase 4B (Integration into LatestEpisodeView)

Scope: Frontend-only integration. No backend/API/schema changes.

What we changed

- LatestEpisodeView now builds a Stage Map VM and renders <StageMap /> in a right-hand panel.
  - VM: derived via buildStageMapView(episode) — pure, no mutations.
  - Selected day: passes selectedDayIndex from the same source that drives storyboard/timeline.
- Added responsive two-column layout in LatestEpisodeView.module.css:
  - Desktop: grid with left (storyboard/detail) and right (map + agents) columns.
  - Mobile: stacks to a single column.
- Accessibility:
  - Stage Map wrapper section role="region" with aria-label:
    - "Stage map for Day {N}" when a valid day is selected.
    - "Stage map (no day selected)" otherwise.
  - The StageMap component itself retains role="group"/role="img" semantics per tile.
  - Added data-testid="stage-map-group" to the StageMap wrapper to make tests more robust in jsdom environments.

Behavior

- Read-only: No new interactions were added to StageMap.
- Selection source of truth unchanged: Timeline and DayStoryboard continue to set selectedDayIndex. StageMap only reflects it.
- Defensive fallbacks preserved: When selectedDayIndex is out of range, StageMap shows its neutral state (“No day selected”).

Tests

- Extended route test LatestEpisodeView.test.tsx:
  - Verifies Stage Map region renders for Day 0 initially (selectedDayIndex seeded from first day).
  - Asserts tile data-tension-tier reflects the selected day, avoiding brittle cross-panel interaction chains.
  - Uses resilient selectors (data-testid, role+label) and fireEvent; avoids flakiness from async scrolling.
- Component tests for StageMap tightened queries and neutral-state checks when no day is selected or out of range.
- All existing route/component/VM tests remain green.

Files touched

- ui-stage/src/routes/LatestEpisodeView.tsx
- ui-stage/src/routes/LatestEpisodeView.module.css
- ui-stage/src/routes/LatestEpisodeView.test.tsx
- ui-stage/src/components/StageMap/index.tsx (added data-testid on wrapper)
- ui-stage/src/components/StageMap/StageMap.test.tsx (query robustness)

Constraints & Stability

- Backend/API/schema unchanged.
- EpisodeViewModel shape untouched; StageMap VM is additive and derived.
- Existing behavior for storyboard/timeline selection and AgentBeliefMiniPanel preserved.

Confirmation

- Frontend-only, no schema/API changes. The VM and component remain additive and optional.

Notes / Future work

- In Phase 4C we can add subtle hover/selection transitions between storyboard and map tiles to suggest a living world, while remaining light on animations.
