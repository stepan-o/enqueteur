from __future__ import annotations

import pytest

from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.systems.base import (
    SystemContext,
    SimulationRNG,
    ECSCommandBuffer,
    WorldViewsHandle,
)
from backend.sim4.ecs.systems.scheduler_order import (
    PHASE_B_SYSTEMS,
    PHASE_C_SYSTEMS,
    PHASE_D_SYSTEMS,
    PHASE_E_SYSTEMS,
)


class DummyWorldViews:  # satisfies WorldViewsHandle Protocol for this sprint
    """Minimal dummy implementation of WorldViewsHandle for integration tests."""

    def get_room_bounds(self, room_id: int):
        _ = room_id
        return None


def make_dummy_world() -> ECSWorld:
    """
    For skeleton integration, an empty world is acceptable — systems will
    simply iterate over empty query results. If future tests need data,
    entities/components can be added here.
    """
    return ECSWorld()


def make_dummy_ctx(world: ECSWorld, seed: int = 123) -> SystemContext:
    rng = SimulationRNG(seed=seed)
    views: WorldViewsHandle = DummyWorldViews()
    commands = ECSCommandBuffer()
    return SystemContext(
        world=world,
        dt=0.1,
        rng=rng,
        views=views,
        commands=commands,
        tick_index=0,
    )


def _run_all_phases_once(ctx: SystemContext) -> None:
    # Phase B
    for SystemClass in PHASE_B_SYSTEMS:
        system = SystemClass()
        system.run(ctx)

    # Phase C
    for SystemClass in PHASE_C_SYSTEMS:
        system = SystemClass()
        system.run(ctx)

    # Phase D
    for SystemClass in PHASE_D_SYSTEMS:
        system = SystemClass()
        system.run(ctx)

    # Phase E
    for SystemClass in PHASE_E_SYSTEMS:
        system = SystemClass()
        system.run(ctx)


def test_full_system_pipeline_runs_for_multiple_ticks():
    world = make_dummy_world()
    ctx = make_dummy_ctx(world=world, seed=123)

    # Run a few ticks to simulate scheduler usage.
    num_ticks = 3
    for tick in range(num_ticks):
        ctx.tick_index = tick
        _run_all_phases_once(ctx)

    # Skeleton systems should not enqueue any commands yet.
    assert ctx.commands.commands == []


def test_integration_rng_remains_usable():
    world = make_dummy_world()
    ctx = make_dummy_ctx(world=world, seed=123)

    before = ctx.rng.random()
    _run_all_phases_once(ctx)
    after = ctx.rng.random()

    # Ensure RNG remains callable and returns floats; exact value is not constrained.
    assert isinstance(before, float)
    assert isinstance(after, float)
