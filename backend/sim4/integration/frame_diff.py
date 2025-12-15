from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .schema import (
    TickFrame,
    AgentFrame,
    ItemFrame,
    IntegrationSchemaVersion,
)


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

    Includes only viewer-relevant changes:
    - tick/time update (scalar header)
    - agent movement (room/x/y changes)
    - agent spawn/despawn
    - item spawn/despawn

    Determinism: all lists are pre-sorted by stable keys (agent_id/item_id).
    """

    # Scalar timebase updates for the next frame
    tick_index: int
    time_seconds: float

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

    return FrameDiff(
        tick_index=curr.tick_index,
        time_seconds=curr.time_seconds,
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
        agents.pop(aid, None)
    for iid in diff.items_despawned:
        items.pop(iid, None)

    # Add spawned (overwrite if present – should not happen, but deterministic)
    for a in diff.agents_spawned:
        agents[a.agent_id] = a
    for it in diff.items_spawned:
        items[it.item_id] = it

    # Apply moves
    for m in diff.agents_moved:
        a = agents.get(m.agent_id)
        if a is None:
            # Movement for a non-existent agent (e.g., malformed diff) — ignore deterministically
            continue
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

    # Rooms: Phase 1 diff does not alter rooms; keep as-is from prior frame
    rooms = frame.rooms

    # Events and narrative fragments are out of scope for diffs (Phase 1). Keep identical to prev.
    events = frame.events
    narrative = frame.narrative_fragments

    return TickFrame(
        schema_version=frame.schema_version if isinstance(frame.schema_version, IntegrationSchemaVersion) else IntegrationSchemaVersion(1, 0, 0),
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
