import pytest

from backend.sim4.runtime.clock import TickClock
from backend.sim4.runtime.tick import tick, TickResult
from backend.sim4.snapshot.output import TickOutputSink
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.world.context import WorldContext, RoomRecord


def make_min_world():
    clock = TickClock()
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    world_ctx.register_room(RoomRecord(id=1, label="A"))
    return clock, ecs_world, world_ctx


def test_phase_h_emits_snapshot_via_output_sink():
    clock, ecs_world, world_ctx = make_min_world()

    collector = []

    class _Sink(TickOutputSink):
        def on_tick_output(
            self,
            *,
            tick_index: int,
            dt: float,
            world_snapshot,
            runtime_events,
            narrative_fragments,
        ) -> None:
            collector.append((tick_index, dt, world_snapshot, list(runtime_events)))

    result = tick(
        clock,
        ecs_world,
        world_ctx,
        rng_seed=123,
        system_scheduler=None,
        previous_events=None,
        tick_output_sink=_Sink(),
        run_id=111,
    )

    assert isinstance(result, TickResult)
    # Sink should have received exactly one snapshot payload
    assert len(collector) == 1
    tick_index, dt, snapshot, _events = collector[0]

    # Basic consistency
    assert hasattr(snapshot, "tick_index")
    assert snapshot.tick_index == result.tick_index
    assert tick_index == result.tick_index
    assert dt == result.dt


def test_phase_h_determinism_same_inputs_same_sorted_events():
    # First run
    clock1, ecs1, world1 = make_min_world()
    collector1 = []
    sink1 = None
    class _Sink1(TickOutputSink):
        def on_tick_output(
            self,
            *,
            tick_index: int,
            dt: float,
            world_snapshot,
            runtime_events,
            narrative_fragments,
        ) -> None:
            collector1.append((world_snapshot, list(runtime_events)))
    sink1 = _Sink1()
    r1 = tick(
        clock1,
        ecs1,
        world1,
        rng_seed=7,
        system_scheduler=None,
        previous_events=None,
        tick_output_sink=sink1,
        run_id=1,
    )
    assert len(collector1) == 1
    f1 = collector1[0][1]

    # Second run with identical starting state
    clock2, ecs2, world2 = make_min_world()
    collector2 = []
    sink2 = None
    class _Sink2(TickOutputSink):
        def on_tick_output(
            self,
            *,
            tick_index: int,
            dt: float,
            world_snapshot,
            runtime_events,
            narrative_fragments,
        ) -> None:
            collector2.append((world_snapshot, list(runtime_events)))
    sink2 = _Sink2()
    r2 = tick(
        clock2,
        ecs2,
        world2,
        rng_seed=7,
        system_scheduler=None,
        previous_events=None,
        tick_output_sink=sink2,
        run_id=1,
    )
    assert len(collector2) == 1
    f2 = collector2[0][1]

    # Compare deterministic parts: events are normalized+sorted deterministically
    assert f1 == f2
