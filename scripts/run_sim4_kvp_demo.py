from __future__ import annotations

"""
Sim4 -> KVP-0001 offline run recorder.

Default profile: ~1 minute at 30 Hz, written to:
  runs/kvp_demo_1min/
"""

from pathlib import Path
import argparse
import math
import random
import shutil
import sys

# Ensure repository root is on sys.path so `backend` package imports work when run directly
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.sim4.runtime.clock import TickClock
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.query import QuerySignature
from backend.sim4.ecs.systems.base import SystemContext
from backend.sim4.ecs.components.embodiment import Transform, RoomPresence
from backend.sim4.ecs.components.intent_action import ActionState
from backend.sim4.ecs.components.work import WorkDesire, WorkAssignment
from backend.sim4.ecs.components.agent_stats import AgentStats
from backend.sim4.ecs.systems.work_desire_system import WorkDesireSystem
from backend.sim4.ecs.systems.work_assignment_system import WorkAssignmentSystem
from backend.sim4.ecs.systems.workstation_movement_system import WorkstationMovementSystem
from backend.sim4.ecs.systems.object_workstation_system import ObjectWorkstationSystem
from backend.sim4.ecs.systems.agent_stats_system import AgentStatsSystem
from backend.sim4.world.context import WorldContext, ItemRecord
from backend.sim4.world.commands import WorldCommand, WorldCommandKind
from backend.sim4.host.sim_runner import SimRunner, OfflineExportConfig
from backend.sim4.host.kvp_defaults import (
    default_run_anchors,
    default_render_spec,
    tick_rate_hz_from_clock,
)
from backend.sim4.world.mbam_layout import apply_mbam_layout
from backend.sim4.runtime.object_bootstrap import (
    spawn_object_entities,
    ensure_world_metrics_entity,
)


class DemoScheduler:
    def __init__(self, mapping: dict[str, list[type]]) -> None:
        self._mapping = mapping

    def iter_phase_systems(self, phase: str):
        return self._mapping.get(phase, [])


class WanderSystem:
    base_positions: dict[int, tuple[float, float]] = {}
    amp_x: float = 2.8
    amp_y: float = 2.0
    freq: float = 0.03
    phase_stride: float = 0.7

    def run(self, ctx: SystemContext) -> None:  # type: ignore[override]
        sig = QuerySignature(read=(Transform,), write=(Transform,))
        for row in ctx.world.query(sig):
            entity = row.entity
            transform = row.components[0]
            base = self.base_positions.get(entity, (transform.x, transform.y))
            phase = ctx.tick_index * self.freq + entity * self.phase_stride
            x = base[0] + self.amp_x * math.sin(phase)
            y = base[1] + self.amp_y * math.cos(phase * 0.9)
            orient = phase % (2.0 * math.pi)
            ctx.commands.set_field(entity, Transform, "x", x)
            ctx.commands.set_field(entity, Transform, "y", y)
            ctx.commands.set_field(entity, Transform, "orientation", orient)


class ActionPulseSystem:
    interval_ticks: int = 30
    modes: int = 5

    def run(self, ctx: SystemContext) -> None:  # type: ignore[override]
        sig = QuerySignature(read=(ActionState,), write=(ActionState,))
        for row in ctx.world.query(sig):
            entity = row.entity
            action = row.components[0]
            if ctx.tick_index % self.interval_ticks == 0:
                new_mode = (action.mode_code + 1 + (entity % 3)) % self.modes
                ctx.commands.set_field(entity, ActionState, "mode_code", new_mode)
                ctx.commands.set_field(entity, ActionState, "time_in_mode", 0.0)
                ctx.commands.set_field(entity, ActionState, "last_mode_change_tick", ctx.tick_index)
            else:
                ctx.commands.set_field(
                    entity,
                    ActionState,
                    "time_in_mode",
                    action.time_in_mode + ctx.dt,
                )


def build_world(num_agents: int) -> tuple[WorldContext, ECSWorld, list[int], list[int], list[int]]:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    room_ids = sorted(world_ctx.rooms_by_id.keys())

    # Doors (from layout, if defined)
    door_ids = sorted(world_ctx.door_open.keys())

    ecs_world = ECSWorld()
    agent_ids: list[int] = []

    for i in range(num_agents):
        room_id = room_ids[i % len(room_ids)]
        room = world_ctx.rooms_by_id[room_id]
        bounds = room.bounds
        center_x = (bounds.min_x + bounds.max_x) / 2.0
        center_y = (bounds.min_y + bounds.max_y) / 2.0
        span_x = max(1.0, (bounds.max_x - bounds.min_x) * 0.35)
        span_y = max(1.0, (bounds.max_y - bounds.min_y) * 0.35)
        jitter_x = ((i % 3) - 1) * span_x * 0.3
        jitter_y = (((i + 1) % 3) - 1) * span_y * 0.3
        base_x = center_x + jitter_x
        base_y = center_y + jitter_y

        desire_seed = random.uniform(0.1, 0.6)
        entity_id = ecs_world.create_entity(
            [
                Transform(room_id=room_id, x=base_x, y=base_y, orientation=0.0),
                RoomPresence(room_id=room_id, time_in_room=0.0),
                ActionState(mode_code=(i % 3), time_in_mode=0.0, last_mode_change_tick=0),
                WorkDesire(
                    value=desire_seed,
                    threshold=0.7,
                    increase_rate=0.012,
                    last_tick=0,
                ),
                WorkAssignment(object_id=None, load_band=0, ticks_working=0),
                AgentStats(
                    durability=random.uniform(0.75, 1.0),
                    energy=random.uniform(0.5, 0.9),
                    money=random.uniform(5.0, 35.0),
                    smartness=random.uniform(0.4, 0.9),
                    toughness=random.uniform(0.4, 0.9),
                    obedience=random.uniform(0.3, 0.9),
                    mission_alignment=random.uniform(0.3, 0.9),
                ),
            ]
        )
        agent_ids.append(entity_id)
        world_ctx.register_agent(entity_id, room_id=room_id)
        WanderSystem.base_positions[entity_id] = (base_x, base_y)

    # Seed a few initial items
    for i in range(min(6, num_agents * 2)):
        item_id = 100 + i
        room_id = room_ids[i % len(room_ids)]
        world_ctx.register_item(ItemRecord(id=item_id, room_id=room_id))

    spawn_object_entities(ecs_world, world_ctx)
    ensure_world_metrics_entity(ecs_world)

    return world_ctx, ecs_world, agent_ids, door_ids, room_ids


def build_ui_events(num_ticks: int, room_ids: list[int], agent_ids: list[int], seed: int) -> list[dict]:
    rng = random.Random(seed)
    events: list[dict] = []
    event_id = 0
    for tick in range(1, num_ticks + 1, 45):
        room_id = room_ids[event_id % len(room_ids)]
        events.append(
            {
                "tick": tick,
                "event_id": f"room_pulse_{event_id}",
                "kind": "room_pulse",
                "data": {"room_id": room_id},
            }
        )
        if agent_ids:
            agent_id = agent_ids[event_id % len(agent_ids)]
            jitter = rng.randint(0, 6)
            events.append(
                {
                    "tick": min(num_ticks, tick + jitter),
                    "event_id": f"agent_notice_{event_id}",
                    "kind": "agent_notice",
                    "data": {"agent_id": agent_id, "room_id": room_id},
                }
            )
        event_id += 1
    return events


def build_psycho_frames(num_ticks: int, agent_ids: list[int], seed: int) -> list[dict]:
    rng = random.Random(seed + 99)
    frames: list[dict] = []
    for tick in range(1, num_ticks + 1, 20):
        nodes = []
        for aid in agent_ids:
            nodes.append(
                {
                    "id": aid,
                    "data": {
                        "mood": round(rng.random(), 3),
                        "energy": round(rng.random(), 3),
                    },
                }
            )
        frames.append({"tick": tick, "nodes": nodes, "edges": []})
    return frames


def make_world_commands_provider(
    room_ids: list[int],
    door_ids: list[int],
    *,
    spawn_every: int,
    item_lifespan: int,
    base_item_id: int,
    door_toggle_every: int,
):
    def world_commands_for_tick(tick_index: int) -> list[WorldCommand]:
        cmds: list[WorldCommand] = []

        # Item spawn/despawn cadence
        if tick_index % spawn_every == 0:
            spawn_index = tick_index // spawn_every
            item_id = base_item_id + spawn_index
            room_id = room_ids[item_id % len(room_ids)]
            cmds.append(
                WorldCommand(
                    seq=0,
                    kind=WorldCommandKind.SPAWN_ITEM,
                    item_id=item_id,
                    room_id=room_id,
                )
            )

            if tick_index >= item_lifespan:
                despawn_index = (tick_index - item_lifespan) // spawn_every
                old_item_id = base_item_id + despawn_index
                cmds.append(
                    WorldCommand(
                        seq=1,
                        kind=WorldCommandKind.DESPAWN_ITEM,
                        item_id=old_item_id,
                    )
                )

        # Door toggle cadence
        if door_ids and tick_index % door_toggle_every == 0:
            door_idx = (tick_index // door_toggle_every) % len(door_ids)
            door_id = door_ids[door_idx]
            if (tick_index // door_toggle_every) % 2 == 0:
                cmds.append(
                    WorldCommand(seq=10, kind=WorldCommandKind.OPEN_DOOR, door_id=door_id)
                )
            else:
                cmds.append(
                    WorldCommand(seq=10, kind=WorldCommandKind.CLOSE_DOOR, door_id=door_id)
                )

        return cmds

    return world_commands_for_tick


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a KVP-0001 demo run for Sim4.")
    p.add_argument("--ticks", type=int, default=1800, help="Number of ticks to run (default: 1800 ~ 1 min @ 30Hz).")
    p.add_argument("--tick-rate", type=int, default=30, help="Tick rate in Hz (default: 30).")
    p.add_argument("--run-root", type=str, default="runs/kvp_demo_1min", help="Output directory.")
    p.add_argument("--agents", type=int, default=6, help="Number of agents to seed.")
    p.add_argument("--seed", type=int, default=123, help="RNG seed for run anchors.")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    world_ctx, ecs_world, agent_ids, door_ids, room_ids = build_world(args.agents)
    clock = TickClock(dt=1.0 / float(args.tick_rate))

    run_root = _REPO_ROOT / args.run_root
    if run_root.exists():
        if not run_root.is_dir():
            raise ValueError(f"run_root exists but is not a directory: {run_root}")
        shutil.rmtree(run_root)

    ui_events = build_ui_events(int(args.ticks), room_ids, agent_ids, int(args.seed))
    psycho_frames = build_psycho_frames(int(args.ticks), agent_ids, int(args.seed))

    offline = OfflineExportConfig(
        run_root=run_root,
        channels=["WORLD", "AGENTS", "ITEMS", "EVENTS", "DEBUG"],
        keyframe_interval=int(args.tick_rate * 2),
        validate=True,
        ui_events=ui_events,
        psycho_frames=psycho_frames,
    )

    run_anchors = default_run_anchors(
        seed=int(args.seed),
        tick_rate_hz=tick_rate_hz_from_clock(clock),
        time_origin_ms=0,
    )
    render_spec = default_render_spec()

    scheduler = DemoScheduler(
        {
            "B": [WanderSystem, ActionPulseSystem],
            "C": [WorkDesireSystem],
            "D": [WorkAssignmentSystem, WorkstationMovementSystem, ObjectWorkstationSystem, AgentStatsSystem],
        }
    )

    world_commands_provider = make_world_commands_provider(
        room_ids=room_ids,
        door_ids=door_ids,
        spawn_every=10,
        item_lifespan=300,
        base_item_id=1000,
        door_toggle_every=45,
    )

    runner = SimRunner(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=int(args.seed),
        system_scheduler=scheduler,
        run_anchors=run_anchors,
        render_spec=render_spec,
        channels=["WORLD", "AGENTS", "ITEMS", "EVENTS", "DEBUG"],
        offline=offline,
    )

    runner.run(num_ticks=int(args.ticks), world_commands_provider=world_commands_provider)
    print(f"Wrote artifacts to: {run_root}")


if __name__ == "__main__":
    main()
