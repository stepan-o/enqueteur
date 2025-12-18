from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .schema import (
    TickFrame,
    AgentFrame,
    ItemFrame,
    RoomFrame,
    EventFrame,
    IntegrationSchemaVersion,
)
from .util.stable_hash import stable_hash


@dataclass(frozen=True)
class AgentMove:
    """Movement/change for a single agent between two frames.

    Primitives-only and Rust-portable. Values are already quantized in frames.
    Sorted by agent_id by the diff builder.
    """

    agent_id: int
    from_room_id: int | None
    to_room_id: int | None
    from_x: float
    from_y: float
    to_x: float
    to_y: float


@dataclass(frozen=True)
class FrameDiff:
    """Viewer-facing frame diff (primitives-only; Phase 1 scope).

    Phase 1 policy: rooms/events/narrative are replace-lists; Phase 2 may introduce structural diffs.

    Includes viewer-relevant data needed to reconstruct the full TickFrame:
    - tick/time update (scalar header)
    - rooms/events/narrative_fragments as replace-lists (Phase 1 policy)
    - agent movement (room/x/y changes)
    - agent spawn/despawn
    - item spawn/despawn

    Determinism: all lists are pre-sorted by stable keys (agent_id/item_id).
    """

    # Scalar timebase updates for the next frame
    tick_index: int
    time_seconds: float

    # Replace-lists for full viewer reconstruction (copied from curr)
    rooms: List[RoomFrame]
    events: List[EventFrame]
    narrative_fragments: List[dict]

    # Changes
    agents_moved: List[AgentMove]
    agents_spawned: List[AgentFrame]
    agents_despawned: List[int]

    items_spawned: List[ItemFrame]
    items_despawned: List[int]


def _agents_by_id(frame: TickFrame) -> dict[int, AgentFrame]:
    return {a.agent_id: a for a in frame.agents}


def _items_by_id(frame: TickFrame) -> dict[int, ItemFrame]:
    return {i.item_id: i for i in frame.items}


def compute_frame_diff(prev: TickFrame, curr: TickFrame) -> FrameDiff:
    """Compute a deterministic, primitives-only diff between two viewer frames.

    Only viewer-relevant changes are encoded per Phase 1 scope.
    Collections in the returned diff are deterministically sorted.
    """
    prev_agents = _agents_by_id(prev)
    curr_agents = _agents_by_id(curr)

    prev_items = _items_by_id(prev)
    curr_items = _items_by_id(curr)

    # Agent spawns/despawns
    prev_a_ids = set(prev_agents.keys())
    curr_a_ids = set(curr_agents.keys())
    spawned_a_ids = sorted(curr_a_ids - prev_a_ids)
    despawned_a_ids = sorted(prev_a_ids - curr_a_ids)

    agents_spawned = [curr_agents[aid] for aid in spawned_a_ids]
    agents_despawned = despawned_a_ids

    # Agent moves (only for persistent agents)
    moved: List[AgentMove] = []
    for aid in sorted(prev_a_ids & curr_a_ids):
        pa = prev_agents[aid]
        ca = curr_agents[aid]
        if pa.room_id != ca.room_id or pa.x != ca.x or pa.y != ca.y:
            moved.append(
                AgentMove(
                    agent_id=aid,
                    from_room_id=pa.room_id,
                    to_room_id=ca.room_id,
                    from_x=pa.x,
                    from_y=pa.y,
                    to_x=ca.x,
                    to_y=ca.y,
                )
            )

    # Items spawns/despawns
    prev_i_ids = set(prev_items.keys())
    curr_i_ids = set(curr_items.keys())
    spawned_i_ids = sorted(curr_i_ids - prev_i_ids)
    despawned_i_ids = sorted(prev_i_ids - curr_i_ids)

    items_spawned = [curr_items[iid] for iid in spawned_i_ids]
    items_despawned = despawned_i_ids

    # Ensure deterministic sorting for spawned lists by id
    agents_spawned.sort(key=lambda a: a.agent_id)
    items_spawned.sort(key=lambda it: it.item_id)

    # Replace-list payloads from current frame, deterministically sorted
    rooms: List[RoomFrame] = list(curr.rooms)
    rooms.sort(key=lambda r: r.room_id)

    # Events: sort by (tick_index, kind, stable_hash(payload)) deterministically
    events: List[EventFrame] = list(curr.events)
    events.sort(key=lambda e: (int(e.tick_index), str(e.kind), stable_hash(e.payload)))

    # Narrative fragments: sort by (tick/idx, importance DESC, agent_id, room_id)
    default_tick = int(curr.tick_index)
    narrative = [dict(d) for d in (curr.narrative_fragments or [])]
    for d in narrative:
        if "tick" not in d and "tick_index" not in d:
            d["tick_index"] = default_tick
    narrative.sort(
        key=lambda d: (
            int(d.get("tick", d.get("tick_index", default_tick)) or default_tick),
            -int(d.get("importance", 0) or 0),
            int(d.get("agent_id", 0) or 0),
            int(d.get("room_id", 0) or 0),
        )
    )

    return FrameDiff(
        tick_index=curr.tick_index,
        time_seconds=curr.time_seconds,
        rooms=rooms,
        events=events,
        narrative_fragments=narrative,
        agents_moved=moved,
        agents_spawned=agents_spawned,
        agents_despawned=agents_despawned,
        items_spawned=items_spawned,
        items_despawned=items_despawned,
    )


def apply_frame_diff(frame: TickFrame, diff: FrameDiff) -> TickFrame:
    """Apply a diff to a prior TickFrame to reconstruct the next TickFrame.

    Deterministic and primitives-only. Does not modify the input frame.
    """
    # Start with maps for agents/items
    agents = _agents_by_id(frame)
    items = _items_by_id(frame)

    # Remove despawned
    for aid in diff.agents_despawned:
        # If missing, consider it a malformed diff
        if aid not in agents:
            raise ValueError(f"Despawn references missing agent_id={aid}")
        agents.pop(aid, None)
    for iid in diff.items_despawned:
        if iid not in items:
            raise ValueError(f"Despawn references missing item_id={iid}")
        items.pop(iid, None)

    # Add spawned — fail fast if ID already exists to prevent corruption
    for a in diff.agents_spawned:
        if a.agent_id in agents:
            raise ValueError(f"Spawn duplicates existing agent_id={a.agent_id}")
        agents[a.agent_id] = a
    for it in diff.items_spawned:
        if it.item_id in items:
            raise ValueError(f"Spawn duplicates existing item_id={it.item_id}")
        items[it.item_id] = it

    # Apply moves
    for m in diff.agents_moved:
        a = agents.get(m.agent_id)
        if a is None:
            # Movement for a non-existent agent is malformed
            raise ValueError(f"Move references missing agent_id={m.agent_id}")
        # Rebuild AgentFrame with updated fields while preserving action_state_code
        agents[m.agent_id] = AgentFrame(
            agent_id=a.agent_id,
            room_id=m.to_room_id,
            x=m.to_x,
            y=m.to_y,
            action_state_code=a.action_state_code,
        )

    # Deterministic ordering
    next_agents = sorted(agents.values(), key=lambda a: a.agent_id)
    next_items = sorted(items.values(), key=lambda it: it.item_id)

    # Replace lists from the diff for full reconstruction
    rooms = list(sorted(diff.rooms, key=lambda r: r.room_id))
    events = list(sorted(diff.events, key=lambda e: (int(e.tick_index), str(e.kind), stable_hash(e.payload))))
    narrative = [dict(d) for d in diff.narrative_fragments]
    # Ensure narrative sort is canonical
    default_tick = int(diff.tick_index)
    narrative.sort(
        key=lambda d: (
            int(d.get("tick", d.get("tick_index", default_tick)) or default_tick),
            -int(d.get("importance", 0) or 0),
            int(d.get("agent_id", 0) or 0),
            int(d.get("room_id", 0) or 0),
        )
    )

    return TickFrame(
        schema_version=frame.schema_version,
        run_id=frame.run_id,
        episode_id=frame.episode_id,
        tick_index=diff.tick_index,
        time_seconds=diff.time_seconds,
        rooms=rooms,
        agents=next_agents,
        items=next_items,
        events=events,
        narrative_fragments=narrative,
    )


__all__ = [
    "AgentMove",
    "FrameDiff",
    "compute_frame_diff",
    "apply_frame_diff",
]
