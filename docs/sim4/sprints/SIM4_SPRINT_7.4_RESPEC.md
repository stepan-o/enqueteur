# Sprint 7 remainder plan (reframed for “useful to narrative + UI”)

We keep the existing sub-sprints 7.5 and 7.6, but tilt them explicitly toward narrative/UI consumption.

## 🔹 7.5 — Minimal Snapshot Diff for Narrative & UI Hooks

### Goal (updated)
Introduce a forward-compatible **SnapshotDiff** layer that:
* lets runtime answer “what changed since last tick?” in a structured way, and
* can be summarized into diff_summary for NarrativeTickContext, and
* is easy for UI to use for lightweight highlights (agent moved rooms, new items, etc.)

### 7.5.1 Files
* `backend/sim4/snapshot/diff_types.py`
* `backend/sim4/snapshot/snapshot_diff.py` (or `diff_builder.py`), e.g.:
```python
def compute_snapshot_diff(
    prev: WorldSnapshot,
    curr: WorldSnapshot,
) -> SnapshotDiff: ...
```

### 7.5.2 Design principles
* **Read-only & deterministic:**
  * Pure functions, no mutation, no I/O, no RNG.
  * Only consume `WorldSnapshot`; no ECS/world/runtime imports.
* **Minimal but “narrative-friendly”:**
  * We don’t try to diff every field.
  * We do detect exactly the things narrative and UI care about to start:
    * **Agent presence/room changes** (who entered/left which room).
    * **Agent position changes** (for visual “moved vs idle”).
    * **Item spawn/despawn/move**.
  * Everything else can be added later without breaking the public surface.
* Separation of concerns:
  * `SnapshotDiff` is a **rich internal type**.
  * `diff_summary` (NarrativeTickContext) is a **compressed view** derived from SnapshotDiff by runtime/history.

### 7.5.3 Types (proposed)
In `diff_types.py:`
```python
from dataclasses import dataclass
from typing import Dict, List

@dataclass(frozen=True)
class AgentDiff:
    agent_id: int
    prev_room_id: int | None
    curr_room_id: int | None
    moved: bool
    position_changed: bool

@dataclass(frozen=True)
class RoomOccupancyDiff:
    room_id: int
    entered_agent_ids: List[int]   # sorted
    exited_agent_ids: List[int]    # sorted

@dataclass(frozen=True)
class ItemDiff:
    item_id: int
    prev_room_id: int | None
    curr_room_id: int | None
    spawned: bool
    despawned: bool
    moved: bool

@dataclass(frozen=True)
class SnapshotDiff:
    tick_prev: int
    tick_curr: int
    # Maps for quick lookup by ID:
    agent_diffs: Dict[int, AgentDiff]
    room_occupancy: Dict[int, RoomOccupancyDiff]
    item_diffs: Dict[int, ItemDiff]
```

You can keep this very small; the point is structural, not exhaustive.

### 7.5.4 Diff computation rules

In `snapshot_diff.py`:
```python
def compute_snapshot_diff(prev: WorldSnapshot, curr: WorldSnapshot) -> SnapshotDiff:
   ...
```

Rules:
**1. Agent diffs**
   * Compare `prev.agent_index` / `curr.agent_index`.
   * For each `agent_id` in `prev ∪ curr`:
     * `prev_room_id = prev_agent.room_id if present else None`
     * `curr_room_id = curr_agent.room_id if present else None`
     * `moved = prev_room_id != curr_room_id and prev_room_id is not None and curr_room_id is not None`
     * `position_changed = (prev.transform.x, prev.transform.y) != (curr.transform.x, curr.transform.y)`  
     (direct equality is fine at this stage; you can add tolerance later).
**2. Room occupancy diffs**
   * For each room in `prev.rooms ∪ curr.rooms`:
     * `prev_agents = set(prev_room.occupants) (empty if missing)`
     * `curr_agents = set(curr_room.occupants)`
     * `entered = sorted(curr_agents - prev_agents)`
     * `exited = sorted(prev_agents - curr_agents)`
   * Only create RoomOccupancyDiff for rooms where entered or exited is non-empty.
**3. Item diffs**
   * Similar to agents:
     * `spawned` = item in `curr but not `prev`.
     * `despawned` = item in `prev` but not `curr`.
     * `moved` = present in both but `room_id` changed.
**4. Determinism**
   * All lists sorted by ID.
   * No reliance on dict iteration order; always sort keys first.

### 7.5.5 Narrative/UI summary helper (lightweight)
We don’t feed `SnapshotDiff` directly into narrative; instead we give runtime a helper to build a small dict:
```python
def summarize_diff_for_narrative(diff: SnapshotDiff) -> dict:
  """
  Produce a compact, JSON-like summary for NarrativeTickContext.diff_summary.
  Fields are intentionally small and stable for LLM use and Rust interop.
  """
```

Example structure:
```python
{
  "moved_agents": [int, ...],             # agent_ids that changed room or position
  "room_entries": {                       # room_id -> [entered agent_ids]
      "1": [3, 5],
      "2": [7],
  },
  "room_exits": {                         # room_id -> [exited agent_ids]
      "1": [2],
  },
  "spawned_items": [item_id, ...],
  "despawned_items": [item_id, ...],
}
```
Runtime will:
* call `compute_snapshot_diff(prev_snapshot, curr_snapshot)`,
* store `SnapshotDiff` if wanted for history/debug,
* pass **only** the summarized dict into `NarrativeTickContext.diff_summary`.

### 7.5.6 Tests
Add tests under `backend/sim4/snapshot/tests/` (or wherever your snapshot tests live):
**1. test_snapshot_diff_agent_movement**
   * prev: agent in room 1 at (0,0)
   * curr: same agent in room 2 at (0,0)
   * Expect:
     * `AgentDiff.moved == True`, `position_changed == False`
     * Room 1 exits contains agent
     * Room 2 entries contains agent
**2. test_snapshot_diff_position_change_no_room_change**
  * prev/curr same room, different (x,y).
  * `moved == False`, `position_changed == True`
**3. test_snapshot_diff_item_spawn_despawn**
  * Items added/removed between snapshots.
**4. test_summarize_diff_for_narrative_shape**
  * Create a small diff and assert summary dict has the expected keys and sorted IDs.

### 7.5.7 Exit criteria (updated)
✅ SnapshotDiff types exist and are Rust-portable DTOs.
✅ compute_snapshot_diff(prev, curr) returns deterministic diffs for agents, rooms, and items.
✅ summarize_diff_for_narrative(diff) produces a small dict suitable for NarrativeTickContext.diff_summary.
✅ No imports from ECS/world/runtime in snapshot diff code; pure snapshot layer.

## 🔹 7.6 — Sprint 7 Closure & API Polish for Narrative Consumption
### Goal (updated)
Make the snapshot package **ready for Sprint 8 narrative work:**
* A clean import surface for runtime/narrative.
* Clear docs on:
  * what exactly snapshots + diffs provide,
  * how narrative should use them,
  * what’s deliberately left for later.

### 7.6.1 Files
* `backend/sim4/snapshot/__init__.py`
* SOT updates:
  * SOT-SIM4-SNAPSHOT-AND-EPISODE (status + diff mention)
  * SOT-SIM4-NARRATIVE-INTERFACE (clarified diff_summary)
* Implementation report:
  * Add “Sprint 7 Snapshot Layer” section.

### 7.6.2 `snapshot/__init__.py` surface

Expose exactly what runtime and narrative will need:
```python
from .world_snapshot import (
    WorldSnapshot,
    RoomSnapshot,
    AgentSnapshot,
    ItemSnapshot,
    TransformSnapshot,
)

from .episode_types import (
    EpisodeMeta,
    EpisodeMood,
    TensionSample,
    SceneSnapshot,
    DayWithScenes,
    EpisodeNarrativeFragment,
    StageEpisodeV2,
)

from .world_snapshot_builder import build_world_snapshot
from .episode_builder import (
    start_new_episode,
    append_tick_to_episode,
    finalize_episode,
)

from .diff_types import (
    SnapshotDiff,
    AgentDiff,
    RoomOccupancyDiff,
    ItemDiff,
)

from .snapshot_diff import (
    compute_snapshot_diff,
    summarize_diff_for_narrative,
)

__all__ = [
    # snapshots
    "WorldSnapshot",
    "RoomSnapshot",
    "AgentSnapshot",
    "ItemSnapshot",
    "TransformSnapshot",
    # episodes
    "EpisodeMeta",
    "EpisodeMood",
    "TensionSample",
    "SceneSnapshot",
    "DayWithScenes",
    "EpisodeNarrativeFragment",
    "StageEpisodeV2",
    # builders
    "build_world_snapshot",
    "start_new_episode",
    "append_tick_to_episode",
    "finalize_episode",
    # diffs
    "SnapshotDiff",
    "AgentDiff",
    "RoomOccupancyDiff",
    "ItemDiff",
    "compute_snapshot_diff",
    "summarize_diff_for_narrative",
]
```

This gives runtime one nice import:
```python
from backend.sim4.snapshot import (
    build_world_snapshot,
    start_new_episode,
    append_tick_to_episode,
    finalize_episode,
    WorldSnapshot,
    StageEpisodeV2,
    compute_snapshot_diff,
    summarize_diff_for_narrative,
)
```

…which matches your original closure task plus the new diff helpers.

### 7.6.3 SOT updates
#### A. SOT-SIM4-SNAPSHOT-AND-EPISODE
* Add a “Status” block at the top or end:
Status (Sprint 7)
> * WorldSnapshot/RoomSnapshot/AgentSnapshot/ItemSnapshot implemented as specified.
> * world_snapshot_builder.py builds deterministic snapshots from WorldContext + ECSWorld.
> * StageEpisodeV2 + episode_builder.py implemented with minimal bookkeeping semantics.
> * SnapshotDiff (optional) implemented for agent/room/item movement deltas.
> * Episode mood, scene segmentation, and advanced aggregation are deferred to Sprint 8+.
* Add a short “Snapshot Diffs” section as mentioned in 1.2.

#### B. SOT-SIM4-NARRATIVE-INTERFACE
* Clarify diff_summary as coming from SnapshotDiff.
* Optionally add a one-liner somewhere in §4.1:

> Runtime constructs NarrativeTickContext.diff_summary by computing a SnapshotDiff between the last two WorldSnapshots and compressing it via a fixed summarization helper.

That’s enough to make the narrative contract unambiguous.

### 7.6.4 Implementation report addendum
Append a “Sprint 7 – Snapshot & Episode Layer” section to your existing Sim4 Implementation Overview. It should:
* Summarize:
  * snapshot DTOs,
  * world_snapshot_builder behavior,
  * episode_builder minimal lifecycle,
  * SnapshotDiff + helpers.
* Emphasize:
  * deterministic, read-only nature,
  * how runtime will use them in Phase H,
  * how narrative will see:
    * `world_snapshot`,
    * `agent_snapshots`,
    * `diff_summary`,
    * later: `StageEpisodeV2` in episode summaries.

Just enough so future-you (or next architect) doesn’t have to re-parse the code.

### 7.6.5 Runtime stub wiring (optional but nice)
In `runtime` (or your tick module), you can add **type-level stubs** so Sprint 8 has clear hooks, even if they’re not fully wired yet:
* Define `NarrativeTickContext` dataclass using:
  * `WorldSnapshot`
  * `list[AgentSnapshot]`
  * `diff_summary: dict`
* Don’t call narrative yet; just prepare the context type and maybe a TODO:

# TODO[NARRATIVE-S8]: call NarrativeEngineInterface.run_tick_jobs(ctx)

This will make Sprint 8 much smoother.

### 7.6.6 Exit criteria (updated)
✅ `backend/sim4/snapshot/__init__.py` exposes the canonical snapshot API (builders, DTOs, diff helpers).
✅ SOT-SIM4-SNAPSHOT-AND-EPISODE updated with “Implemented in Sprint 7” + diff mention.
✅ SOT-SIM4-NARRATIVE-INTERFACE updated so `diff_summary` is clearly defined as a summary derived from SnapshotDiff.
✅ Implementation report includes a concise “Snapshot & Episode Layer” section.
✅ Runtime can `import backend.sim4.snapshot` cleanly and has a clear mental (and type-level) model of how snapshots and diffs will be fed into narrative in Sprint 8.