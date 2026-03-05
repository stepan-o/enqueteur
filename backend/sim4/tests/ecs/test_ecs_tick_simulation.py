from __future__ import annotations

from dataclasses import dataclass

from backend.sim4.ecs import ECSWorld
from backend.sim4.ecs.query import QuerySignature
from backend.sim4.ecs.systems.base import ECSCommandBuffer


@dataclass
class Health:
    value: int


def test_healing_tick_updates_health():
    world = ECSWorld()
    # Setup: create a single entity with Health 10
    e = world.create_entity(initial_components=[Health(value=10)])

    # Tick logic via command buffer: heal to 15
    buf = ECSCommandBuffer()
    buf.set_field(entity_id=e, component_type=Health, field_name="value", value=15)

    # Apply commands (production path)
    world.apply_commands(buf.commands)

    # Verify final state
    h = world.get_component(e, Health)
    assert h is not None
    assert h.value == 15


def test_spawn_and_modify_entities_via_commands():
    world = ECSWorld()

    # First tick: create two entities via commands
    buf = ECSCommandBuffer()
    buf.create_entity(components=[Health(value=1)])
    buf.create_entity(components=[Health(value=10)])
    world.apply_commands(buf.commands)

    # Discover entities with Health using the query API
    signature = QuerySignature(read=(Health,), write=())
    results = list(world.query(signature))
    # Expect exactly two entities
    assert len(results) == 2
    # Collect in ascending entity id order
    entity_ids = [row.entity for row in results]

    # Second tick: update their health values deterministically
    buf = ECSCommandBuffer()
    # Map lowest ID -> 2, highest ID -> 20
    buf.set_field(entity_ids[0], Health, "value", 2)
    buf.set_field(entity_ids[1], Health, "value", 20)
    world.apply_commands(buf.commands)

    # Re-query and assert final values
    signature = QuerySignature(read=(Health,), write=())
    results2 = list(world.query(signature))
    assert len(results2) == 2
    # Results are ordered by entity ID deterministically
    row0, row1 = results2
    assert row0.entity == entity_ids[0] and row1.entity == entity_ids[1]
    (h0,) = row0.components
    (h1,) = row1.components
    assert isinstance(h0, Health) and isinstance(h1, Health)
    assert {h0.value, h1.value} == {2, 20}


def _run_tick_scenario_snapshot() -> list[tuple[int, int]]:
    """
    Helper that sets up a world, runs a mini deterministic scenario via
    ECSCommandBuffer + apply_commands, and returns a comparable snapshot
    of (entity_id, health_value) pairs sorted by entity_id.
    """
    world = ECSWorld()

    # Initial setup via direct world API (allowed for setup only)
    e0 = world.create_entity(initial_components=[Health(value=3)])
    e1 = world.create_entity(initial_components=[Health(value=7)])

    # Build deterministic command sequence
    buf = ECSCommandBuffer()
    buf.set_field(e0, Health, "value", 5)
    buf.set_field(e1, Health, "value", 10)
    buf.create_entity(components=[Health(value=1)])

    # Apply
    world.apply_commands(buf.commands)

    # Build snapshot via query
    snapshot: list[tuple[int, int]] = []
    signature = QuerySignature(read=(Health,), write=())
    for row in world.query(signature):
        (h,) = row.components
        snapshot.append((int(row.entity), h.value))
    snapshot.sort(key=lambda p: p[0])
    return snapshot


def test_tick_scenario_is_deterministic():
    snap1 = _run_tick_scenario_snapshot()
    snap2 = _run_tick_scenario_snapshot()
    assert snap1 == snap2
