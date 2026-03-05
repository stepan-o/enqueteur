import pytest

from backend.sim4.runtime.clock import TickClock
from backend.sim4.runtime.tick import tick, TickResult
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.world.context import WorldContext, RoomRecord
from backend.sim4.world.views import WorldViews
from backend.sim4.ecs.systems.base import SystemContext, SimulationRNG, ECSCommandBuffer, WorldViewsHandle
from backend.sim4.ecs.commands import ECSCommandKind


# --- Local dummy views to satisfy WorldViewsHandle if needed ---
class DummyViews(WorldViewsHandle):
    pass


# --- No-op system (enqueues no commands) ---
class NoopSystem:
    def run(self, ctx: SystemContext) -> None:  # type: ignore[override]
        # read dt and tick_index to ensure context is usable
        _ = (ctx.dt, ctx.tick_index)
        # no commands enqueued
        return


# --- Command system: enqueues a single CREATE_ENTITY command ---
class CommandSystem:
    def run(self, ctx: SystemContext) -> None:  # type: ignore[override]
        ctx.commands.create_entity([])


class DummyScheduler:
    def __init__(self, mapping):
        self._mapping = mapping

    def iter_phase_systems(self, phase: str):
        return self._mapping.get(phase, [])


def _mk_world_with_room() -> WorldContext:
    wc = WorldContext()
    wc.register_room(RoomRecord(id=1, label="A"))
    return wc


def test_noop_system_runs_and_produces_no_commands():
    clock = TickClock()
    ecs_world = ECSWorld()
    world_ctx = _mk_world_with_room()

    scheduler = DummyScheduler({"B": [NoopSystem]})

    result = tick(
        clock,
        ecs_world,
        world_ctx,
        rng_seed=123,
        system_scheduler=scheduler,
        previous_events=None,
    )

    assert isinstance(result, TickResult)
    assert result.ecs_commands == []


def test_command_system_enqueues_one_create_entity():
    clock = TickClock()
    ecs_world = ECSWorld()
    world_ctx = _mk_world_with_room()

    scheduler = DummyScheduler({"C": [CommandSystem]})

    result = tick(
        clock,
        ecs_world,
        world_ctx,
        rng_seed=42,
        system_scheduler=scheduler,
        previous_events=None,
    )

    assert len(result.ecs_commands) == 1
    cmd = result.ecs_commands[0]
    assert cmd.kind is ECSCommandKind.CREATE_ENTITY


def test_determinism_same_seed_same_commands():
    ecs_world1 = ECSWorld()
    ecs_world2 = ECSWorld()
    world_ctx1 = _mk_world_with_room()
    world_ctx2 = _mk_world_with_room()
    sched = DummyScheduler({"B": [CommandSystem]})

    clock1 = TickClock()
    r1 = tick(clock1, ecs_world1, world_ctx1, rng_seed=999, system_scheduler=sched)

    clock2 = TickClock()
    r2 = tick(clock2, ecs_world2, world_ctx2, rng_seed=999, system_scheduler=sched)

    kinds1 = [c.kind for c in r1.ecs_commands]
    kinds2 = [c.kind for c in r2.ecs_commands]
    assert kinds1 == kinds2
