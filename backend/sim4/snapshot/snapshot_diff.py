from __future__ import annotations

from typing import Dict, List, Tuple

from backend.sim4.snapshot.world_snapshot import WorldSnapshot
from backend.sim4.snapshot.diff_types import (
    SnapshotDiff,
    AgentDiff,
    RoomOccupancyDiff,
    ItemDiff,
)


def compute_snapshot_diff(prev: WorldSnapshot, curr: WorldSnapshot) -> SnapshotDiff:
    """
    Compute a minimal, deterministic diff between two WorldSnapshots.

    Scope (Sub‑Sprint 7.5):
    - Agent room changes and position changes.
    - Room occupancy entered/exited agents.
    - Item spawn/despawn and room moves.

    Notes:
    - Pure transformation over snapshots; no mutation; no I/O; no RNG.
    - Only uses snapshot DTOs; no imports from ecs/world/runtime/narrative.
    """

    # --- Agent diffs ---
    prev_agent_index = prev.agent_index or {}
    curr_agent_index = curr.agent_index or {}
    all_agent_ids = sorted(set(prev_agent_index.keys()) | set(curr_agent_index.keys()))

    agent_diffs: Dict[int, AgentDiff] = {}
    for aid in all_agent_ids:
        prev_agent = prev.agents[prev_agent_index[aid]] if aid in prev_agent_index else None
        curr_agent = curr.agents[curr_agent_index[aid]] if aid in curr_agent_index else None

        prev_room_id = prev_agent.room_id if prev_agent is not None else None
        curr_room_id = curr_agent.room_id if curr_agent is not None else None

        moved = (
            prev_room_id is not None
            and curr_room_id is not None
            and prev_room_id != curr_room_id
        )

        position_changed = False
        if prev_agent is not None and curr_agent is not None:
            prev_pos: Tuple[float, float] = (prev_agent.transform.x, prev_agent.transform.y)
            curr_pos: Tuple[float, float] = (curr_agent.transform.x, curr_agent.transform.y)
            position_changed = prev_pos != curr_pos

        agent_diffs[aid] = AgentDiff(
            agent_id=aid,
            prev_room_id=prev_room_id,
            curr_room_id=curr_room_id,
            moved=moved,
            position_changed=position_changed,
        )

    # --- Room occupancy diffs ---
    prev_rooms_by_id: Dict[int, List[int]] = {r.room_id: r.occupants for r in prev.rooms}
    curr_rooms_by_id: Dict[int, List[int]] = {r.room_id: r.occupants for r in curr.rooms}
    all_room_ids = sorted(set(prev_rooms_by_id.keys()) | set(curr_rooms_by_id.keys()))

    room_occupancy: Dict[int, RoomOccupancyDiff] = {}
    for rid in all_room_ids:
        prev_agents = set(prev_rooms_by_id.get(rid, []))
        curr_agents = set(curr_rooms_by_id.get(rid, []))
        entered = sorted(curr_agents - prev_agents)
        exited = sorted(prev_agents - curr_agents)
        if entered or exited:
            room_occupancy[rid] = RoomOccupancyDiff(
                room_id=rid, entered_agent_ids=entered, exited_agent_ids=exited
            )

    # --- Item diffs ---
    prev_items_by_id: Dict[int, int | None] = {it.item_id: it.room_id for it in prev.items}
    curr_items_by_id: Dict[int, int | None] = {it.item_id: it.room_id for it in curr.items}
    all_item_ids = sorted(set(prev_items_by_id.keys()) | set(curr_items_by_id.keys()))

    item_diffs: Dict[int, ItemDiff] = {}
    for iid in all_item_ids:
        prev_room_id_i = prev_items_by_id.get(iid, None) if iid in prev_items_by_id else None
        curr_room_id_i = curr_items_by_id.get(iid, None) if iid in curr_items_by_id else None
        prev_exists = iid in prev_items_by_id
        curr_exists = iid in curr_items_by_id
        spawned = (not prev_exists) and curr_exists
        despawned = prev_exists and (not curr_exists)
        moved_item = prev_exists and curr_exists and (prev_room_id_i != curr_room_id_i)
        item_diffs[iid] = ItemDiff(
            item_id=iid,
            prev_room_id=prev_room_id_i,
            curr_room_id=curr_room_id_i,
            spawned=spawned,
            despawned=despawned,
            moved=moved_item,
        )

    return SnapshotDiff(
        tick_prev=prev.tick_index,
        tick_curr=curr.tick_index,
        agent_diffs=agent_diffs,
        room_occupancy=room_occupancy,
        item_diffs=item_diffs,
    )


def summarize_diff_for_narrative(diff: SnapshotDiff) -> dict:
    """
    Produce a compact, JSON-like summary for NarrativeTickContext.diff_summary.
    Fields are intentionally small and stable for LLM use and Rust interop.
    """

    # moved_agents: any agent with moved or position_changed
    moved_agents = sorted(
        aid
        for aid, ad in diff.agent_diffs.items()
        if ad.moved or ad.position_changed
    )

    # room entries/exits: use string keys for JSON friendliness
    room_entries: Dict[str, List[int]] = {}
    room_exits: Dict[str, List[int]] = {}
    for rid in sorted(diff.room_occupancy.keys()):
        ro = diff.room_occupancy[rid]
        if ro.entered_agent_ids:
            room_entries[str(rid)] = list(sorted(ro.entered_agent_ids))
        if ro.exited_agent_ids:
            room_exits[str(rid)] = list(sorted(ro.exited_agent_ids))

    # spawned/despawned items
    spawned_items = sorted([iid for iid, d in diff.item_diffs.items() if d.spawned])
    despawned_items = sorted([iid for iid, d in diff.item_diffs.items() if d.despawned])

    return {
        "moved_agents": moved_agents,
        "room_entries": room_entries,
        "room_exits": room_exits,
        "spawned_items": spawned_items,
        "despawned_items": despawned_items,
    }


__all__ = ["compute_snapshot_diff", "summarize_diff_for_narrative"]
