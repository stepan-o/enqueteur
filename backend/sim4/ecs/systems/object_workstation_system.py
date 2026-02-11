from __future__ import annotations

"""
Phase D system — ObjectWorkstationSystem.

Maintains dynamic object/workstation state, durability/efficiency wear, and
aggregates factory production input each tick.
"""

from typing import Dict, List

from .base import SystemContext
from ..query import QuerySignature
from ..components.embodiment import RoomPresence
from ..components.intent_action import ActionState
from ..components.objects import (
    WorkstationStatus,
    ObjectRef,
    ObjectPlacement,
    ObjectStats,
    WorkstationState,
    ProductionProfile,
    FactoryMetrics,
)


ACTIVE_STATUSES = {
    WorkstationStatus.RUNNING_IDLE,
    WorkstationStatus.PRODUCING_HALF,
    WorkstationStatus.PRODUCING_CAPACITY,
    WorkstationStatus.PRODUCING_OVERDRIVE,
}


class ObjectWorkstationSystem:
    """Phase D: updates workstation state + production metrics."""

    def run(self, ctx: SystemContext) -> None:
        room_agents: Dict[int, List[int]] = {}
        agent_action: Dict[int, int] = {}

        agent_sig = QuerySignature(read=(RoomPresence,), write=(), optional=(ActionState,))
        for row in ctx.world.query(agent_sig):
            rp = row.components[0]
            action = row.components[1] if len(row.components) > 1 else None
            room_agents.setdefault(rp.room_id, []).append(row.entity)
            if action is not None:
                agent_action[row.entity] = int(action.mode_code)

        for agents in room_agents.values():
            agents.sort()

        obj_sig = QuerySignature(
            read=(ObjectRef, ObjectPlacement, ProductionProfile),
            write=(ObjectStats, WorkstationState),
        )

        objects = []
        for row in ctx.world.query(obj_sig):
            oref, placement, profile, stats, ws = row.components
            objects.append((int(oref.object_id), row.entity, placement, profile, stats, ws))

        objects.sort(key=lambda o: (o[2].room_id, o[0]))

        per_room_idx: Dict[int, int] = {}
        factory_input = 0.0
        active_objects = 0
        overdrive_objects = 0

        for object_id, eid, placement, profile, stats, ws in objects:
            agents = room_agents.get(placement.room_id, [])
            idx = per_room_idx.get(placement.room_id, 0)
            per_room_idx[placement.room_id] = idx + 1
            occupant = agents[idx % len(agents)] if agents else None

            status = _safe_status(ws.status_code)

            if status == WorkstationStatus.UNAVAILABLE:
                desired_status = WorkstationStatus.UNAVAILABLE
                occupant = None
            elif stats.durability <= 0.0:
                desired_status = WorkstationStatus.BROKEN
                occupant = None
            elif occupant is None:
                desired_status = WorkstationStatus.NOT_OCCUPIED
            else:
                action_code = agent_action.get(occupant, 0)
                desired_status = _status_from_agent(action_code, stats.efficiency)

            ticks_in_state = ws.ticks_in_state + 1
            if desired_status != status or occupant != ws.occupant_agent_id:
                ticks_in_state = 0

            durability = stats.durability
            efficiency = stats.efficiency

            if desired_status in ACTIVE_STATUSES:
                wear = profile.wear_rate_idle if desired_status == WorkstationStatus.RUNNING_IDLE else profile.wear_rate_load
                decay = (
                    profile.efficiency_decay_idle
                    if desired_status == WorkstationStatus.RUNNING_IDLE
                    else profile.efficiency_decay_load
                )
                if desired_status == WorkstationStatus.PRODUCING_OVERDRIVE:
                    wear *= profile.overdrive_wear_multiplier
                    decay *= profile.overdrive_wear_multiplier
                durability = max(0.0, durability - wear * ctx.dt)
                efficiency = max(0.0, efficiency - decay * ctx.dt)
            elif desired_status == WorkstationStatus.NOT_OCCUPIED:
                efficiency = min(1.0, efficiency + profile.efficiency_recovery_idle * ctx.dt)

            if durability <= 0.0:
                desired_status = WorkstationStatus.BROKEN
                occupant = None

            output_multiplier = _output_multiplier(desired_status, profile.overdrive_multiplier)
            output = profile.base_output * efficiency * output_multiplier
            factory_input += output
            if desired_status in ACTIVE_STATUSES:
                active_objects += 1
            if desired_status == WorkstationStatus.PRODUCING_OVERDRIVE:
                overdrive_objects += 1

            if durability != stats.durability:
                ctx.commands.set_field(eid, ObjectStats, "durability", durability)
            if efficiency != stats.efficiency:
                ctx.commands.set_field(eid, ObjectStats, "efficiency", efficiency)
            if desired_status != status:
                ctx.commands.set_field(eid, WorkstationState, "status_code", int(desired_status))
            if occupant != ws.occupant_agent_id:
                ctx.commands.set_field(eid, WorkstationState, "occupant_agent_id", occupant)
            if ticks_in_state != ws.ticks_in_state:
                ctx.commands.set_field(eid, WorkstationState, "ticks_in_state", int(ticks_in_state))

        metrics_sig = QuerySignature(read=(FactoryMetrics,), write=(FactoryMetrics,))
        metrics_rows = list(ctx.world.query(metrics_sig))
        if metrics_rows:
            metrics_entity = min(row.entity for row in metrics_rows)
            ctx.commands.set_field(metrics_entity, FactoryMetrics, "factory_input", factory_input)
            ctx.commands.set_field(metrics_entity, FactoryMetrics, "active_objects", int(active_objects))
            ctx.commands.set_field(metrics_entity, FactoryMetrics, "overdrive_objects", int(overdrive_objects))


def _safe_status(code: int) -> WorkstationStatus:
    try:
        return WorkstationStatus(int(code))
    except Exception:
        return WorkstationStatus.NOT_OCCUPIED


def _status_from_agent(action_code: int, efficiency: float) -> WorkstationStatus:
    if efficiency <= 0.15:
        return WorkstationStatus.RUNNING_IDLE
    band = int(action_code) % 4
    if band == 0:
        return WorkstationStatus.RUNNING_IDLE
    if band == 1:
        return WorkstationStatus.PRODUCING_HALF
    if band == 2:
        return WorkstationStatus.PRODUCING_CAPACITY
    return (
        WorkstationStatus.PRODUCING_OVERDRIVE
        if efficiency >= 0.6
        else WorkstationStatus.PRODUCING_CAPACITY
    )


def _output_multiplier(status: WorkstationStatus, overdrive_multiplier: float) -> float:
    if status == WorkstationStatus.RUNNING_IDLE:
        return 0.1
    if status == WorkstationStatus.PRODUCING_HALF:
        return 0.5
    if status == WorkstationStatus.PRODUCING_CAPACITY:
        return 1.0
    if status == WorkstationStatus.PRODUCING_OVERDRIVE:
        return float(overdrive_multiplier)
    return 0.0


__all__ = ["ObjectWorkstationSystem"]
