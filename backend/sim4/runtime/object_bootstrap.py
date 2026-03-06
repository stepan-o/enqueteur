"""Runtime bootstrap helpers for object entities + world metrics."""

from __future__ import annotations

from typing import List

from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.query import QuerySignature
from backend.sim4.ecs.components.objects import (
    WorkstationStatus,
    ObjectRef,
    ObjectClass,
    ObjectPlacement,
    ObjectStats,
    WorkstationState,
    ProductionProfile,
    WorldMetrics,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.object_catalog import get_object_class_spec


def spawn_object_entities(ecs_world: ECSWorld, world_ctx: WorldContext) -> List[int]:
    """Create ECS entities for every ObjectRecord in WorldContext."""
    created: List[int] = []
    for oid in sorted(world_ctx.objects_by_id.keys()):
        rec = world_ctx.objects_by_id[oid]
        spec = get_object_class_spec(rec.class_code)
        eid = ecs_world.create_entity(
            [
                ObjectRef(object_id=oid),
                ObjectClass(class_code=rec.class_code),
                ObjectPlacement(
                    room_id=rec.room_id,
                    tile_x=rec.tile_x,
                    tile_y=rec.tile_y,
                    size_w=rec.size_w,
                    size_h=rec.size_h,
                    orientation=rec.orientation,
                    scale=rec.scale,
                    height=rec.height,
                ),
                ObjectStats(
                    durability=float(spec.durability_max),
                    efficiency=float(spec.efficiency_base),
                ),
                WorkstationState(
                    status_code=int(WorkstationStatus.NOT_OCCUPIED),
                    occupant_agent_id=None,
                    ticks_in_state=0,
                ),
                ProductionProfile(
                    base_output=float(spec.base_output),
                    wear_rate_idle=float(spec.wear_rate_idle),
                    wear_rate_load=float(spec.wear_rate_load),
                    efficiency_decay_idle=float(spec.efficiency_decay_idle),
                    efficiency_decay_load=float(spec.efficiency_decay_load),
                    efficiency_recovery_idle=float(spec.efficiency_recovery_idle),
                    overdrive_multiplier=float(spec.overdrive_multiplier),
                    overdrive_wear_multiplier=float(spec.overdrive_wear_multiplier),
                ),
            ]
        )
        created.append(eid)
    return created


def ensure_world_metrics_entity(ecs_world: ECSWorld) -> int:
    """Ensure a singleton WorldMetrics entity exists; return its entity id."""
    sig = QuerySignature(read=(WorldMetrics,), write=())
    rows = ecs_world.query(sig)
    existing_ids = [row.entity for row in rows]
    if existing_ids:
        return sorted(existing_ids)[0]
    return ecs_world.create_entity([WorldMetrics(world_output=0.0, active_objects=0, overdrive_objects=0)])


__all__ = ["spawn_object_entities", "ensure_world_metrics_entity"]
