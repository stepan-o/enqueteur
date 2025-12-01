from __future__ import annotations

from dataclasses import dataclass

from backend.sim4.ecs import ECSWorld
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
    results = world.query((Health,)).to_list()
    # Expect exactly two entities
    assert len(results) == 2
    # Collect in ascending entity id order
    entity_ids = [eid for eid, (_h,) in results]

    # Second tick: update their health values deterministically
    buf = ECSCommandBuffer()
    # Map lowest ID -> 2, highest ID -> 20
    buf.set_field(entity_ids[0], Health, "value", 2)
    buf.set_field(entity_ids[1], Health, "value", 20)
    world.apply_commands(buf.commands)

    # Re-query and assert final values
    results2 = world.query((Health,)).to_list()
    assert len(results2) == 2
    # Results are ordered by entity ID deterministically
    (e0, (h0,)), (e1, (h1,)) = results2
    assert e0 == entity_ids[0] and e1 == entity_ids[1]
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
    for eid, (h,) in world.query((Health,)):
        snapshot.append((int(eid), h.value))
    snapshot.sort(key=lambda p: p[0])
    return snapshot


def test_tick_scenario_is_deterministic():
    snap1 = _run_tick_scenario_snapshot()
    snap2 = _run_tick_scenario_snapshot()
    assert snap1 == snap2
