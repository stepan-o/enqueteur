from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.systems.base import (
    SimulationRNG,
    WorldViewsHandle,
    SystemContext,
    ECSCommandBuffer,
)


@dataclass
class DummyWorldViews:
    """
    Minimal dummy implementation of WorldViewsHandle for tests.
    All methods are no-ops or return empty iterables.
    """

    def get_room_bounds(self, room_id: int):
        _ = room_id
        return None


def make_dummy_world() -> ECSWorld:
    return ECSWorld()


def test_simulation_rng_deterministic():
    seed = 12345
    rng1 = SimulationRNG(seed)
    rng2 = SimulationRNG(seed)

    values1 = [rng1.random() for _ in range(5)]
    values2 = [rng2.random() for _ in range(5)]

    assert values1 == values2


def test_simulation_rng_uniform_deterministic():
    seed = 999
    rng1 = SimulationRNG(seed)
    rng2 = SimulationRNG(seed)

    values1 = [rng1.uniform(-1.0, 1.0) for _ in range(5)]
    values2 = [rng2.uniform(-1.0, 1.0) for _ in range(5)]

    assert values1 == values2


def test_system_context_construction():
    world = make_dummy_world()
    rng = SimulationRNG(seed=42)
    views = DummyWorldViews()
    commands = ECSCommandBuffer()

    ctx = SystemContext(
        world=world,
        dt=0.1,
        rng=rng,
        views=views,
        commands=commands,
        tick_index=0,
    )

    assert ctx.world is world
    assert ctx.dt == 0.1
    assert ctx.rng is rng
    assert ctx.views is views
    assert ctx.commands is commands
    assert ctx.tick_index == 0


def test_ecs_command_buffer_sequences_and_copy():
    buffer = ECSCommandBuffer()

    class DummyComponent:
        def __init__(self, value: int) -> None:
            self.value = value

    # Enqueue some commands
    buffer.set_field(entity_id=1, component_type=DummyComponent, field_name="value", value=10)
    buffer.create_entity(components=[DummyComponent(1)])
    buffer.destroy_entity(entity_id=2)

    commands = buffer.commands

    # Ensure we got 3 commands
    assert len(commands) == 3

    # Ensure seq is monotonic 0,1,2
    seqs = [c.seq for c in commands]
    assert seqs == [0, 1, 2]

    # Defensive copy
    commands.pop()
    commands2 = buffer.commands
    assert len(commands2) == 3
