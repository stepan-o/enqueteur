from __future__ import annotations

"""
WorldSnapshot builder (Sub‑Sprint 7.3).

Deterministically constructs a WorldSnapshot from:
- WorldContext (rooms, items, indices)
- ECSWorld (agents/components)

Rules (per SOT-SIM4-SNAPSHOT-AND-EPISODE §6.1):
- Read-only; no mutations; no I/O; no RNG or wall clock.
- All collections explicitly sorted; never rely on dict/set iteration order.
- Minimal viable fields for agents/items; many fields are stubbed with
  empty values by design in this sub-sprint.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from backend.sim4.snapshot.world_snapshot import (
    WorldSnapshot,
    RoomSnapshot,
    RoomBoundsSnapshot,
    AgentSnapshot,
    ItemSnapshot,
    ObjectSnapshot,
    TransformSnapshot,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.views import WorldViews
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.components.embodiment import Transform, RoomPresence
from backend.sim4.ecs.components.intent_action import ActionState
from backend.sim4.ecs.components.narrative_state import NarrativeState
from backend.sim4.ecs.query import QuerySignature
from backend.sim4.ecs.components.objects import (
    ObjectRef,
    ObjectClass,
    ObjectPlacement,
    ObjectStats,
    WorkstationState,
    FactoryMetrics,
)


def _build_rooms(world_ctx: WorldContext) -> List[RoomSnapshot]:
    views = WorldViews(world_ctx)
    room_ids = list(world_ctx.rooms_by_id.keys())
    room_ids.sort()
    rooms: List[RoomSnapshot] = []
    for rid in room_ids:
        rec = world_ctx.rooms_by_id[rid]
        # Occupants/items via views for read-only containers
        occupants = sorted(list(views.get_room_agents(rid)))
        items = sorted(list(views.get_room_items(rid)))
        neighbors = sorted(list(views.iter_room_neighbors(rid)))
        bounds = None
        if rec.bounds is not None:
            bounds = RoomBoundsSnapshot(
                min_x=float(rec.bounds.min_x),
                min_y=float(rec.bounds.min_y),
                max_x=float(rec.bounds.max_x),
                max_y=float(rec.bounds.max_y),
            )
        rooms.append(
            RoomSnapshot(
                room_id=rid,
                label=rec.label or "",
                kind_code=int(rec.kind_code),
                occupants=occupants,
                items=items,
                neighbors=neighbors,
                tension_tier=rec.tension_tier if rec.tension_tier is not None else "low",
                highlight=rec.highlight if rec.highlight is not None else False,
                height=float(rec.height) if rec.height is not None else None,
                bounds=bounds,
                zone=rec.zone,
                level=int(rec.level),
            )
        )
    return rooms


def _build_agents(ecs_world: ECSWorld) -> List[AgentSnapshot]:
    agent_ids = list(ecs_world.iter_entity_ids())
    # iter_entity_ids already returns a sorted iterator; still make a list to be explicit
    agents: List[AgentSnapshot] = []
    for aid in agent_ids:
        # Required embodiment
        t: Transform | None = ecs_world.get_component(aid, Transform)  # type: ignore[name-defined]
        rp: RoomPresence | None = ecs_world.get_component(aid, RoomPresence)  # type: ignore[name-defined]
        if t is None or rp is None:
            # Skip entities that are not agents (must have Transform + RoomPresence)
            continue

        act: ActionState | None = ecs_world.get_component(aid, ActionState)  # type: ignore[name-defined]
        narr: NarrativeState | None = ecs_world.get_component(aid, NarrativeState)  # type: ignore[name-defined]

        transform = TransformSnapshot(room_id=rp.room_id if rp else None, x=t.x, y=t.y)
        action_state_code = act.mode_code if act is not None else 0
        narrative_state_ref = narr.narrative_id if narr is not None else None
        cached_summary_ref = narr.cached_summary_ref if narr is not None else None

        agents.append(
            AgentSnapshot(
                agent_id=aid,
                room_id=rp.room_id if rp is not None else None,
                # Identity & Persona (stubs)
                role_code=0,
                generation=0,
                profile_traits={},
                identity_vector=[],
                persona_style_vector=None,
                # Drives & Emotion (stubs)
                drives={},
                emotions={},
                # Social / Intent & Planning (stubs)
                key_relationships=[],
                active_motives=[],
                plan=None,
                # Action & Embodiment
                transform=transform,
                action_state_code=action_state_code,
                # Narrative Overlay
                narrative_state_ref=narrative_state_ref,
                cached_summary_ref=cached_summary_ref,
            )
        )

    # Ensure deterministic ascending by agent_id
    agents.sort(key=lambda a: a.agent_id)
    return agents


def _build_items(world_ctx: WorldContext) -> List[ItemSnapshot]:
    items: List[ItemSnapshot] = []
    item_ids = list(world_ctx.items_by_id.keys())
    item_ids.sort()
    for iid in item_ids:
        item = world_ctx.items_by_id[iid]
        items.append(
            ItemSnapshot(
                item_id=iid,
                room_id=item.room_id,
                owner_agent_id=None,
                status_code=0,
                label="",
            )
        )
    return items


def _build_objects(ecs_world: ECSWorld) -> List[ObjectSnapshot]:
    objects: List[ObjectSnapshot] = []
    sig = QuerySignature(
        read=(ObjectRef, ObjectClass, ObjectPlacement, ObjectStats, WorkstationState),
        write=(),
    )
    rows = []
    for row in ecs_world.query(sig):
        oref, ocls, placement, stats, ws = row.components
        rows.append((int(oref.object_id), ocls, placement, stats, ws))

    rows.sort(key=lambda r: r[0])
    for oid, ocls, placement, stats, ws in rows:
        objects.append(
            ObjectSnapshot(
                object_id=oid,
                class_code=ocls.class_code,
                room_id=int(placement.room_id),
                tile_x=int(placement.tile_x),
                tile_y=int(placement.tile_y),
                size_w=int(placement.size_w),
                size_h=int(placement.size_h),
                orientation=int(placement.orientation),
                scale=float(placement.scale),
                height=float(placement.height) if placement.height is not None else None,
                durability=float(stats.durability),
                efficiency=float(stats.efficiency),
                status_code=int(ws.status_code),
                occupant_agent_id=int(ws.occupant_agent_id) if ws.occupant_agent_id is not None else None,
                ticks_in_state=int(ws.ticks_in_state),
            )
        )
    return objects


def _build_factory_input(ecs_world: ECSWorld) -> float:
    sig = QuerySignature(read=(FactoryMetrics,), write=())
    rows = list(ecs_world.query(sig))
    if not rows:
        return 0.0
    metrics = rows[0].components[0]
    return float(metrics.factory_input)


def build_world_snapshot(
    tick_index: int,
    episode_id: int,
    world_ctx: WorldContext,
    ecs_world: ECSWorld,
) -> WorldSnapshot:
    """Build a deterministic WorldSnapshot from WorldContext + ECSWorld.

    Notes:
    - world_id and time_seconds may not yet exist on WorldContext; use fallbacks.
    - This function performs no mutation and relies only on read-only accessors.
    """

    rooms = _build_rooms(world_ctx)
    agents = _build_agents(ecs_world)
    items = _build_items(world_ctx)
    objects = _build_objects(ecs_world)
    factory_input = _build_factory_input(ecs_world)

    # Indices mapping IDs to positional indices in the lists
    room_index: Dict[int, int] = {r.room_id: idx for idx, r in enumerate(rooms)}
    agent_index: Dict[int, int] = {a.agent_id: idx for idx, a in enumerate(agents)}

    # Fallbacks for world identity / time (not yet present in WorldContext)
    world_id = 0
    time_seconds = 0.0
    # If the context is extended in future, use those values deterministically
    if hasattr(world_ctx, "identity") and getattr(world_ctx.identity, "world_id", None) is not None:
        try:
            world_id = int(world_ctx.identity.world_id)  # type: ignore[attr-defined]
        except Exception:
            world_id = 0
    if hasattr(world_ctx, "time_seconds") and isinstance(world_ctx.time_seconds, (int, float)):
        time_seconds = float(world_ctx.time_seconds)  # type: ignore[attr-defined]

    return WorldSnapshot(
        world_id=world_id,
        tick_index=tick_index,
        episode_id=episode_id,
        time_seconds=time_seconds,
        factory_input=factory_input,
        rooms=rooms,
        agents=agents,
        items=items,
        objects=objects,
        room_index=room_index,
        agent_index=agent_index,
    )


__all__ = ["build_world_snapshot"]
