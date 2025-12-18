from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from .schema import (
    IntegrationSchemaVersion,
    TickFrame,
    RoomFrame,
    AgentFrame,
    ItemFrame,
    EventFrame,
)
from .util.quantize import qf
from .util.stable_hash import stable_hash
from .types import WorldSnapshotLike
from .render_specs import (
    RoomRenderSpec,
    AgentRenderSpec,
    DEFAULT_ASSETS,
)

if TYPE_CHECKING:
    from backend.sim4.snapshot.world_snapshot import WorldSnapshot


def _to_plain(obj: Any) -> dict:
    if isinstance(obj, Mapping):
        return dict(obj)
    if is_dataclass(obj):
        return asdict(obj)
    out: dict[str, Any] = {}
    for k in dir(obj):
        if k.startswith("_"):
            continue
        try:
            v = getattr(obj, k)
        except Exception:
            continue
        if callable(v):
            continue
        out[k] = v
    return out


def _event_sort_key(e: EventFrame) -> tuple:
    return (int(e.tick_index), str(e.kind), stable_hash(e.payload))


def _build_rooms(snapshot: WorldSnapshotLike) -> list[RoomFrame]:
    rooms = getattr(snapshot, "rooms", []) or []
    out: list[RoomFrame] = []
    for r in rooms:
        room_id = getattr(r, "room_id")
        label = getattr(r, "label", "") or ""
        neighbors = list(getattr(r, "neighbors", []) or [])
        neighbors = [int(n) for n in neighbors]
        neighbors.sort()
        out.append(RoomFrame(room_id=int(room_id), label=str(label), neighbors=neighbors))
    out.sort(key=lambda rf: rf.room_id)
    return out


def _build_agents(snapshot: WorldSnapshotLike) -> list[AgentFrame]:
    agents = getattr(snapshot, "agents", []) or []
    out: list[AgentFrame] = []
    for a in agents:
        agent_id = getattr(a, "agent_id")
        room_id = getattr(a, "room_id", None)
        transform = getattr(a, "transform", None)
        x = getattr(transform, "x", 0.0)
        y = getattr(transform, "y", 0.0)
        action_state_code = getattr(a, "action_state_code", 0)
        out.append(
            AgentFrame(
                agent_id=int(agent_id),
                room_id=int(room_id) if room_id is not None else None,
                x=qf(float(x)),
                y=qf(float(y)),
                action_state_code=int(action_state_code),
            )
        )
    out.sort(key=lambda af: af.agent_id)
    return out


def _build_items(snapshot: WorldSnapshotLike) -> list[ItemFrame]:
    items = getattr(snapshot, "items", []) or []
    out: list[ItemFrame] = []
    for it in items:
        item_id = getattr(it, "item_id")
        room_id = getattr(it, "room_id", None)
        owner = getattr(it, "owner_agent_id", None)
        status_code = getattr(it, "status_code", 0)
        out.append(
            ItemFrame(
                item_id=int(item_id),
                room_id=int(room_id) if room_id is not None else None,
                owner_agent_id=int(owner) if owner is not None else None,
                status_code=int(status_code),
            )
        )
    out.sort(key=lambda itf: itf.item_id)
    return out


def _normalize_events(
    events: Sequence[Any],
    default_tick: int,
) -> list[EventFrame]:
    frames: list[EventFrame] = []
    for e in events or ():
        d = _to_plain(e)
        # tick
        t = d.get("tick")
        if t is None:
            t = d.get("tick_index", default_tick)
        try:
            t = int(t)
        except Exception:
            t = int(default_tick)
        # kind
        kind = d.get("kind") or d.get("type") or d.get("name") or ""
        kind = str(kind)
        # extract common ids if present
        agent_id = d.get("agent_id")
        if agent_id is not None:
            try:
                agent_id = int(agent_id)
            except Exception:
                agent_id = None
        room_id = d.get("room_id")
        if room_id is not None:
            try:
                room_id = int(room_id)
            except Exception:
                room_id = None
        # payload: keep as dict but remove top-level fields we normalized
        payload = dict(d)
        for k in ("tick", "tick_index", "kind", "type", "name", "agent_id", "room_id"):
            payload.pop(k, None)
        frames.append(
            EventFrame(
                tick_index=t,
                kind=kind,
                payload=payload,
                agent_id=agent_id,
                room_id=room_id,
            )
        )
    frames.sort(key=_event_sort_key)
    return frames


def build_tick_frame(
    world_snapshot: WorldSnapshotLike,
    events: Sequence[Any],
    narrative_fragments: Sequence[Any] | None = None,
    *,
    schema_version: IntegrationSchemaVersion | None = None,
    run_id: int | None = None,
) -> TickFrame:
    """Canonical primitives-only TickFrame builder.

    - Does not embed engine DTOs.
    - Deterministically sorts all collections.
    - Quantizes time and agent positions to avoid float drift.
    - Accepts narrative fragments as DTO-like inputs and returns them as plain dicts.
    """
    if schema_version is None:
        schema_version = IntegrationSchemaVersion(1, 0, 0)

    tick_index = int(getattr(world_snapshot, "tick_index"))
    time_seconds = qf(float(getattr(world_snapshot, "time_seconds", 0.0)))
    episode_id = getattr(world_snapshot, "episode_id", None)
    episode_id_int = int(episode_id) if episode_id is not None else None

    rooms = _build_rooms(world_snapshot)
    agents = _build_agents(world_snapshot)
    items = _build_items(world_snapshot)

    event_frames = _normalize_events(events, default_tick=tick_index)

    # Narrative fragments normalized to plain dicts, deterministically sorted by a stable key
    narr_list = [
        _to_plain(n) for n in (narrative_fragments or ())
    ]
    # Apply default tick where missing for determinism in potential downstream usage
    for d in narr_list:
        if "tick" not in d and "tick_index" not in d:
            d["tick_index"] = tick_index
    narr_list.sort(
        key=lambda d: (
            int(d.get("tick", d.get("tick_index", tick_index)) or tick_index),
            -int(d.get("importance", 0) or 0),
            int(d.get("agent_id", 0) or 0),
            int(d.get("room_id", 0) or 0),
        )
    )

    # Build deterministic, placeholder render specs (no layout yet; S12.2)
    room_specs: list[RoomRenderSpec] = []
    for rf in rooms:
        room_specs.append(
            RoomRenderSpec(
                room_id=rf.room_id,
                world_x=0.0,
                world_y=0.0,
                width=1.0,
                height=1.0,
                z_layer=0,
                art_ref=DEFAULT_ASSETS.default_room_art_ref,
            )
        )
    # Sort by numeric room_id if possible, else by string
    def _room_key(rs: RoomRenderSpec):
        try:
            return (0, int(rs.room_id))
        except Exception:
            return (1, str(rs.room_id))
    room_specs.sort(key=_room_key)

    agent_specs: list[AgentRenderSpec] = []
    for af in agents:
        agent_specs.append(
            AgentRenderSpec(
                agent_id=af.agent_id,
                sprite_ref=DEFAULT_ASSETS.default_agent_sprite_ref,
                bubble_anchor_dx=DEFAULT_ASSETS.default_bubble_anchor_dx,
                bubble_anchor_dy=DEFAULT_ASSETS.default_bubble_anchor_dy,
            )
        )
    def _agent_key(aspec: AgentRenderSpec):
        try:
            return (0, int(aspec.agent_id))
        except Exception:
            return (1, str(aspec.agent_id))
    agent_specs.sort(key=_agent_key)

    return TickFrame(
        schema_version=schema_version,
        run_id=run_id,
        episode_id=episode_id_int,
        tick_index=tick_index,
        time_seconds=time_seconds,
        rooms=rooms,
        agents=agents,
        items=items,
        events=event_frames,
        narrative_fragments=narr_list,
        room_render_specs=room_specs,
        agent_render_specs=agent_specs,
    )


__all__ = ["build_tick_frame"]
