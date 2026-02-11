from __future__ import annotations

"""
Phase D system — WorkstationMovementSystem.

Moves agents toward their assigned workstation object and holds them
near the interaction point while working.
"""

import math
from typing import Dict, Tuple

from .base import SystemContext
from ..query import QuerySignature
from ..components.work import WorkAssignment
from ..components.embodiment import Transform, RoomPresence
from ..components.objects import ObjectRef, ObjectPlacement


class WorkstationMovementSystem:
    """Phase D: steer agents to assigned workstation targets."""

    speed_units_per_sec: float = 2.2
    hold_radius: float = 0.25
    stand_offset: float = 0.35

    def run(self, ctx: SystemContext) -> None:
        object_targets: Dict[int, Tuple[int, float, float]] = {}
        obj_sig = QuerySignature(read=(ObjectRef, ObjectPlacement), write=())
        for row in ctx.world.query(obj_sig):
            oref, placement = row.components
            oid = int(oref.object_id)
            room_id = int(placement.room_id)
            bounds = getattr(ctx.views, "get_room_bounds", lambda _rid: None)(room_id)
            origin_x = bounds.min_x if bounds is not None else 0.0
            origin_y = bounds.min_y if bounds is not None else 0.0
            foot_w, foot_h = _footprint_dims(placement.size_w, placement.size_h, placement.orientation)
            cx = origin_x + placement.tile_x + foot_w * 0.5
            cy = origin_y + placement.tile_y + foot_h * 0.5 + (foot_h * 0.5 + self.stand_offset)
            object_targets[oid] = (room_id, float(cx), float(cy))

        agent_sig = QuerySignature(read=(WorkAssignment, Transform, RoomPresence), write=(Transform,))
        for row in ctx.world.query(agent_sig):
            assignment, transform, presence = row.components
            oid = assignment.object_id
            if oid is None:
                continue
            target = object_targets.get(oid)
            if target is None:
                continue
            room_id, tx, ty = target
            if int(presence.room_id) != int(room_id):
                continue

            dx = tx - transform.x
            dy = ty - transform.y
            dist = math.hypot(dx, dy)
            if dist <= self.hold_radius:
                nx = tx
                ny = ty
            else:
                step = min(dist, self.speed_units_per_sec * ctx.dt)
                nx = transform.x + (dx / dist) * step
                ny = transform.y + (dy / dist) * step

            if abs(nx - transform.x) > 1e-4:
                ctx.commands.set_field(row.entity, Transform, "x", nx)
            if abs(ny - transform.y) > 1e-4:
                ctx.commands.set_field(row.entity, Transform, "y", ny)
            if dist > 1e-4:
                orient = math.atan2(dy, dx)
                ctx.commands.set_field(row.entity, Transform, "orientation", orient)


def _footprint_dims(size_w: int, size_h: int, orientation: int) -> Tuple[float, float]:
    if int(orientation) % 2 == 1:
        return float(size_h), float(size_w)
    return float(size_w), float(size_h)


__all__ = ["WorkstationMovementSystem"]
