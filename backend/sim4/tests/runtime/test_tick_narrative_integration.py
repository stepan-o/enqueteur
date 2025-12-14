from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Tuple

from backend.sim4.runtime import TickClock
from backend.sim4.runtime.tick import tick
from backend.sim4.world.context import WorldContext, RoomRecord
from backend.sim4.ecs.world import ECSWorld


class FakeNarrativeRuntimeContext:
    def __init__(self) -> None:
        self.calls: List[Tuple[int, float, int]] = []

    def run_tick_narrative(
        self,
        tick_index: int,
        dt: float,
        episode_id: int,
        world_ctx: WorldContext,
        ecs_world: ECSWorld,
    ) -> None:
        self.calls.append((tick_index, dt, episode_id))


class RaisingNarrativeRuntimeContext(FakeNarrativeRuntimeContext):
    def run_tick_narrative(
        self,
        tick_index: int,
        dt: float,
        episode_id: int,
        world_ctx: WorldContext,
        ecs_world: ECSWorld,
    ) -> None:  # type: ignore[override]
        raise RuntimeError("boom")


class DummyScheduler:
    def iter_phase_systems(self, phase: str):  # pragma: no cover - no systems in these tests
        return []


def make_world() -> tuple[TickClock, WorldContext, ECSWorld]:
    clock = TickClock(dt=1.0)
    wc = WorldContext()
    wc.register_room(RoomRecord(id=1, label="R1"))
    ecs = ECSWorld()
    return clock, wc, ecs


def test_tick_calls_narrative_when_ctx_provided():
    clock, wc, ecs = make_world()
    fake = FakeNarrativeRuntimeContext()
    _res = tick(
        clock=clock,
        ecs_world=ecs,
        world_ctx=wc,
        rng_seed=123,
        system_scheduler=DummyScheduler(),
        world_commands_in=None,
        episode_id=42,
        narrative_ctx=fake,
    )
    # Exactly one call
    assert len(fake.calls) == 1
    # The tick_index after clock.advance(1) is 1
    ti, dt, ep = fake.calls[0]
    assert ti == clock.tick_index  # should match the post-advance tick
    assert ep == 42
    assert dt == clock.dt


def test_tick_skips_narrative_when_ctx_none():
    clock, wc, ecs = make_world()
    # Should run without raising even if narrative is None
    _res = tick(
        clock=clock,
        ecs_world=ecs,
        world_ctx=wc,
        rng_seed=0,
        system_scheduler=DummyScheduler(),
        world_commands_in=None,
        episode_id=1,
        narrative_ctx=None,
    )
    # Nothing to assert beyond "no exception"; ensure tick progressed
    assert clock.tick_index == 1


def test_narrative_exception_does_not_break_tick():
    clock, wc, ecs = make_world()
    raising = RaisingNarrativeRuntimeContext()
    # Should not raise
    _res = tick(
        clock=clock,
        ecs_world=ecs,
        world_ctx=wc,
        rng_seed=0,
        system_scheduler=DummyScheduler(),
        world_commands_in=None,
        episode_id=7,
        narrative_ctx=raising,
    )
    # Tick should have completed
    assert clock.tick_index == 1
