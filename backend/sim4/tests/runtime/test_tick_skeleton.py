import pytest

from backend.sim4.runtime.clock import TickClock
from backend.sim4.runtime.tick import tick, TickResult
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.world.context import WorldContext, RoomRecord


def test_tick_returns_result_and_advances_clock():
    clock = TickClock()
    ecs_world = ECSWorld()
    world_ctx = WorldContext()

    # Minimal preconditions: having at least one room shouldn't be required,
    # but ensure context is valid.
    world_ctx.register_room(RoomRecord(id=1, label="A"))

    result = tick(
        clock,
        ecs_world,
        world_ctx,
        rng_seed=123,
        system_scheduler=object(),
        previous_events=None,
    )

    assert isinstance(result, TickResult)
    assert result.tick_index == 1  # advanced from 0 to 1
    assert pytest.approx(result.dt) == clock.dt
    assert isinstance(result.world_events, list)


def test_tick_multiple_steps_sequential_calls():
    clock = TickClock()
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    world_ctx.register_room(RoomRecord(id=1))

    r1 = tick(clock, ecs_world, world_ctx, rng_seed=1, system_scheduler=None)
    assert r1.tick_index == 1

    r2 = tick(clock, ecs_world, world_ctx, rng_seed=1, system_scheduler=None)
    assert r2.tick_index == 2
