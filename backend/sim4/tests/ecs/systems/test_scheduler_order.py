from __future__ import annotations

import pytest

from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.systems.base import SystemContext, SimulationRNG, ECSCommandBuffer, WorldViewsHandle
from backend.sim4.ecs.systems.scheduler_order import (
    PHASE_B_SYSTEMS,
    PHASE_C_SYSTEMS,
    PHASE_D_SYSTEMS,
    PHASE_E_SYSTEMS,
)


class DummyWorldViews:  # satisfies WorldViewsHandle Protocol for this sprint
    """Minimal dummy implementation of WorldViewsHandle for scheduler tests."""

    def get_room_bounds(self, room_id: int):
        _ = room_id
        return None


def make_dummy_world() -> ECSWorld:
    return ECSWorld()


def make_dummy_ctx(world: ECSWorld, seed: int = 123, tick_index: int = 0) -> SystemContext:
    rng = SimulationRNG(seed=seed)
    views: WorldViewsHandle = DummyWorldViews()
    commands = ECSCommandBuffer()
    return SystemContext(
        world=world,
        dt=0.1,
        rng=rng,
        views=views,
        commands=commands,
        tick_index=tick_index,
    )


def test_scheduler_phase_lists_contain_classes():
    for systems in (PHASE_B_SYSTEMS, PHASE_C_SYSTEMS, PHASE_D_SYSTEMS, PHASE_E_SYSTEMS):
        assert isinstance(systems, list)
        for cls in systems:
            assert callable(cls), f"Expected system class, got {cls!r}"


@pytest.mark.parametrize(
    "phase_systems",
    [PHASE_B_SYSTEMS, PHASE_C_SYSTEMS, PHASE_D_SYSTEMS, PHASE_E_SYSTEMS],
)
def test_each_phase_systems_run_without_error(phase_systems):
    world = make_dummy_world()
    ctx = make_dummy_ctx(world)

    for SystemClass in phase_systems:
        system = SystemClass()
        system.run(ctx)  # Should not raise


def test_scheduler_runs_all_phases_in_order():
    world = make_dummy_world()
    ctx = make_dummy_ctx(world)

    for SystemClass in PHASE_B_SYSTEMS:
        SystemClass().run(ctx)

    for SystemClass in PHASE_C_SYSTEMS:
        SystemClass().run(ctx)

    for SystemClass in PHASE_D_SYSTEMS:
        SystemClass().run(ctx)

    for SystemClass in PHASE_E_SYSTEMS:
        SystemClass().run(ctx)

    # Skeleton systems should not enqueue commands yet
    assert ctx.commands.commands == []
