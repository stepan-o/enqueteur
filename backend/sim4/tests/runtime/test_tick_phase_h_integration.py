import pytest

from backend.sim4.runtime.clock import TickClock
from backend.sim4.runtime.tick import tick, TickResult
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.world.context import WorldContext, RoomRecord


def make_min_world():
    clock = TickClock()
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    world_ctx.register_room(RoomRecord(id=1, label="A"))
    return clock, ecs_world, world_ctx


def test_phase_h_emits_tick_frame_via_sink_and_in_result():
    clock, ecs_world, world_ctx = make_min_world()

    collector = []
    result = tick(
        clock,
        ecs_world,
        world_ctx,
        rng_seed=123,
        system_scheduler=None,
        previous_events=None,
        tick_frame_sink=collector.append,
        run_id=111,
    )

    assert isinstance(result, TickResult)
    # Sink should have received exactly one frame
    assert len(collector) == 1
    frame = collector[0]

    # Basic consistency
    assert hasattr(frame, "tick_index")
    assert frame.tick_index == result.tick_index

    # Result should also carry the frame
    assert result.tick_frame is frame


def test_phase_h_determinism_same_inputs_same_sorted_events():
    # First run
    clock1, ecs1, world1 = make_min_world()
    collector1 = []
    r1 = tick(
        clock1,
        ecs1,
        world1,
        rng_seed=7,
        system_scheduler=None,
        previous_events=None,
        tick_frame_sink=collector1.append,
        run_id=1,
    )
    assert len(collector1) == 1
    f1 = collector1[0]

    # Second run with identical starting state
    clock2, ecs2, world2 = make_min_world()
    collector2 = []
    r2 = tick(
        clock2,
        ecs2,
        world2,
        rng_seed=7,
        system_scheduler=None,
        previous_events=None,
        tick_frame_sink=collector2.append,
        run_id=1,
    )
    assert len(collector2) == 1
    f2 = collector2[0]

    # Compare deterministic parts: events are normalized+sorted deterministically
    assert f1.events == f2.events
