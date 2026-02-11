from __future__ import annotations

"""
Phase D system — WorkAssignmentSystem.

Chooses available workstation objects for agents whose desire crosses
thresholds, and releases assignments when desire falls.
"""

from typing import Dict, List, Optional

from .base import SystemContext
from ..query import QuerySignature
from ..components.work import WorkDesire, WorkAssignment
from ..components.embodiment import RoomPresence
from ..components.objects import WorkstationStatus, ObjectRef, ObjectPlacement, ObjectStats, WorkstationState


class WorkAssignmentSystem:
    """Phase D: deterministic workstation assignment and release."""

    def run(self, ctx: SystemContext) -> None:
        obj_sig = QuerySignature(
            read=(ObjectRef, ObjectPlacement, ObjectStats, WorkstationState),
            write=(WorkstationState,),
        )

        objects_by_room: Dict[int, List[int]] = {}
        object_info: Dict[int, dict] = {}

        for row in ctx.world.query(obj_sig):
            oref, placement, stats, ws = row.components
            oid = int(oref.object_id)
            status = _safe_status(ws.status_code)
            info = {
                "entity_id": row.entity,
                "room_id": int(placement.room_id),
                "status": status,
                "occupant": ws.occupant_agent_id,
                "durability": float(stats.durability),
            }
            object_info[oid] = info
            objects_by_room.setdefault(info["room_id"], []).append(oid)

        for room_id in objects_by_room:
            objects_by_room[room_id].sort()

        agent_sig = QuerySignature(
            read=(WorkDesire, RoomPresence, WorkAssignment),
            write=(WorkAssignment,),
        )

        claimed_objects: Dict[int, int] = {}

        for row in ctx.world.query(agent_sig):
            desire, presence, assignment = row.components
            agent_id = row.entity
            room_id = int(presence.room_id)
            wants_work = desire.value >= desire.threshold

            current_oid = assignment.object_id
            current_info = object_info.get(current_oid) if current_oid is not None else None

            if current_oid is not None:
                mismatched_room = current_info is not None and current_info["room_id"] != room_id
                occupied_by_other = (
                    current_info is not None
                    and current_info["occupant"] is not None
                    and current_info["occupant"] != agent_id
                )
                if (not wants_work) or (current_info is None) or (not _is_available(current_info)) or mismatched_room or occupied_by_other:
                    _release_assignment(ctx, agent_id, current_oid, current_info)
                    current_oid = None

            if current_oid is None and wants_work:
                chosen = _choose_object(objects_by_room.get(room_id, []), object_info, claimed_objects)
                if chosen is not None:
                    chosen_info = object_info[chosen]
                    claimed_objects[chosen] = agent_id
                    _assign_object(ctx, agent_id, chosen, chosen_info, desire)
                    current_oid = chosen

            load_band = _load_band(desire, wants_work)
            if assignment.object_id != current_oid:
                ctx.commands.set_field(agent_id, WorkAssignment, "object_id", current_oid)
                ctx.commands.set_field(agent_id, WorkAssignment, "ticks_working", 0 if current_oid is None else 1)
            if assignment.load_band != load_band:
                ctx.commands.set_field(agent_id, WorkAssignment, "load_band", int(load_band))
            if current_oid is None and assignment.ticks_working != 0:
                ctx.commands.set_field(agent_id, WorkAssignment, "ticks_working", 0)
            elif current_oid is not None and assignment.object_id == current_oid:
                ctx.commands.set_field(agent_id, WorkAssignment, "ticks_working", int(assignment.ticks_working + 1))


def _safe_status(code: int) -> WorkstationStatus:
    try:
        return WorkstationStatus(int(code))
    except Exception:
        return WorkstationStatus.NOT_OCCUPIED


def _is_available(info: dict) -> bool:
    status: WorkstationStatus = info["status"]
    return status not in (WorkstationStatus.UNAVAILABLE, WorkstationStatus.BROKEN) and info["durability"] > 0.0


def _choose_object(
    room_objects: List[int],
    object_info: Dict[int, dict],
    claimed_objects: Dict[int, int],
) -> Optional[int]:
    for oid in room_objects:
        if oid in claimed_objects:
            continue
        info = object_info.get(oid)
        if info is None:
            continue
        if not _is_available(info):
            continue
        if info["occupant"] is None:
            return oid
    return None


def _assign_object(ctx: SystemContext, agent_id: int, object_id: int, info: dict, desire: WorkDesire) -> None:
    entity_id = info["entity_id"]
    if info["occupant"] != agent_id:
        ctx.commands.set_field(entity_id, WorkstationState, "occupant_agent_id", agent_id)
        ctx.commands.set_field(entity_id, WorkstationState, "ticks_in_state", 0)
    if info["status"] == WorkstationStatus.NOT_OCCUPIED:
        ctx.commands.set_field(entity_id, WorkstationState, "status_code", int(WorkstationStatus.RUNNING_IDLE))


def _release_assignment(
    ctx: SystemContext,
    agent_id: int,
    object_id: int,
    info: Optional[dict],
) -> None:
    if info is None:
        return
    entity_id = info["entity_id"]
    if info["occupant"] == agent_id:
        ctx.commands.set_field(entity_id, WorkstationState, "occupant_agent_id", None)
        if info["status"] not in (WorkstationStatus.BROKEN, WorkstationStatus.UNAVAILABLE):
            ctx.commands.set_field(entity_id, WorkstationState, "status_code", int(WorkstationStatus.NOT_OCCUPIED))
        ctx.commands.set_field(entity_id, WorkstationState, "ticks_in_state", 0)


def _load_band(desire: WorkDesire, wants_work: bool) -> int:
    if not wants_work:
        return 0
    excess = max(0.0, desire.value - desire.threshold)
    if excess < 0.1:
        return 0
    if excess < 0.25:
        return 1
    if excess < 0.45:
        return 2
    return 3


__all__ = ["WorkAssignmentSystem"]
