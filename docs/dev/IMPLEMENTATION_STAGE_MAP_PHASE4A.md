### Stage Map — Phase 4A (VM-first, Frontend-only)

This document summarizes the minimal Stage Map implementation for Era II — Phase 4A.

Scope: Frontend-only. No backend/API/schema changes.

What we added

- VM: ui-stage/src/vm/stageMapVm.ts
  - Exports interfaces StageMapRoomVM, StageMapDayVM, StageMapViewModel
  - Exports buildStageMapView(episode: EpisodeViewModel | null | undefined): StageMapViewModel
  - Heuristics documented in code comments
- Component: ui-stage/src/components/StageMap
  - index.tsx: Stateless renderer for a given StageMapViewModel + selectedDayIndex
  - StageMap.module.css: Simple grid of room tiles with low/medium/high visual tints
- Tests:
  - VM tests: ui-stage/src/vm/stageMapVm.test.ts
  - Component tests: ui-stage/src/components/StageMap/StageMap.test.tsx

VM design

- Input: EpisodeViewModel (and its `_raw: StageEpisode`). We do not change EpisodeViewModel shape.
- Rooms: StageEpisode currently has no room structure. We provide a stable synthetic fallback room:
  - id: "factory_floor"; label: "Factory Floor".
  - If real rooms are added in future backend versions, this VM can adopt them without breaking the current interface.
- For each day (by raw.day_index):
  - tensionScore per room: use day.tension_score; default 0 when missing.
  - incidentCount per room: use day.total_incidents; default 0 when missing.
  - primaryAgents: up to 3 agent names from day.agents, sorted by avg_stress desc then name asc.
  - day-level tensionTier thresholds (aligned with DayStoryboard bands):
    - avg < 0.25 → "low"
    - avg < 0.55 → "medium"
    - else → "high"
  - Defensive: malformed inputs return zeros/empties and always build a valid VM. If the episode or days are missing, returns `{ days: [] }`.

Ordering and determinism

- Days: sorted by dayIndex ascending.
- Rooms: sorted by label ascending (future-proof if we add more rooms).
- primaryAgents: sorted by stress desc, then name asc; capped at 3.

Component behavior (<StageMap />)

- Props: { viewModel: StageMapViewModel; selectedDayIndex: number | null }
- If a valid day is selected: render tiles for that day’s rooms.
  - Accessibility: wrapper role="group" aria-label="Stage map".
  - Each tile role="img" with aria-label including room label, tension tier, agent activity summary, and day index.
  - data attributes: data-tension-tier, data-selected
- If null/out-of-range: render neutral map (all rooms at low) with "No day selected" caption.

Known limitations / Future extensions

- No true room geometry yet; grid-only layout.
- Single synthetic room until backend provides room structures.
- Read-only; no interactions beyond visual state.
- No animations beyond CSS transitions.

Files touched

- ui-stage/src/vm/stageMapVm.ts (new)
- ui-stage/src/vm/stageMapVm.test.ts (new)
- ui-stage/src/components/StageMap/index.tsx (new)
- ui-stage/src/components/StageMap/StageMap.module.css (new)
- ui-stage/src/components/StageMap/StageMap.test.tsx (new)
- docs/dev/IMPLEMENTATION_STAGE_MAP_PHASE4A.md (this file)

Tradeoffs

- Chose a single synthetic room to avoid inventing backend schema; ensures stability and forward-compatibility.
- Derived primary agents purely from day-level avg_stress to stay schema-accurate and deterministic.

Contracts & Stability

- Backend/API/schema unchanged.
- VM is additive and optional; no existing consumer contracts altered.
- Tests added to lock behavior and defensiveness.
