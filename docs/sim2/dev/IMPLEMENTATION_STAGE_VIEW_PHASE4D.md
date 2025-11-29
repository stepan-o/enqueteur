### Stage View — Phase 4D (Visual polish + light motion)

Scope: Frontend-only cosmetic uplift. No backend/API/schema changes. No new VMs.

Goals

- Make StageView feel like an early “stage mode” through CSS-only refinements.
- Subtle transitions on state changes; no JS animations.
- Preserve existing ARIA roles, labels, and data-testid hooks.

What changed

- StageMap visuals (ui-stage/src/components/StageMap/StageMap.module.css):
  - Strengthened low/medium/high tier distinction using background tints and borders.
  - Added subtle transitions on background, border, box-shadow, and tiny hover lift for tiles.
  - Added selected-room styling via [data-selected="true"] with border highlight and inner shadow.
  - Agent chips restyled as pill tokens with hover/focus-visible states; semantics unchanged.
  - Neutral “No day selected” state appears slightly muted.

- StageView layout/presentation (ui-stage/src/routes/StageView.module.css, StageView.tsx):
  - Introduced a soft header band in the detail panel that switches between “World view” and “Agent focus”.
  - Moved inline styles for AgentFocus layout to CSS module (agentRow, agentName, agentRole, agentStats, agentTagline).
  - Split WorldSummary into two short lines to increase readability (same information content).
  - Tweaked gaps/padding; ensured responsive grid remains clean under 900px.

- Cleanup:
  - Removed leftover console.log from AppRouter.tsx.

Kept stable

- No changes to props, VM shapes, or route structure.
- ARIA labels and roles unchanged for StageMap wrappers/tiles and StageView regions.
- Data attributes preserved: data-tension-tier, data-selected, data-testid="stage-map-group" and data-testid="agent-focus-panel".

Tests

- No test updates were required; existing StageMap and StageView route tests continue to pass.
- Verified the full ui-stage test suite is green.

Files touched

- ui-stage/src/components/StageMap/StageMap.module.css
- ui-stage/src/routes/StageView.module.css
- ui-stage/src/routes/StageView.tsx
- ui-stage/src/AppRouter.tsx
- docs/dev/IMPLEMENTATION_STAGE_VIEW_PHASE4D.md (this file)

Acceptance

- Frontend-only work, no schema/API changes.
- Subtle motion via CSS transitions only; no new dependencies.
