from __future__ import annotations

from dataclasses import dataclass

from backend.sim4.ecs import ECSWorld
from backend.sim4.ecs.query import QuerySignature


@dataclass
class Position:
    x: float
    y: float


@dataclass
class Velocity:
    dx: float
    dy: float


def test_basic_entity_and_component_lifecycle():
    w = ECSWorld()

    # Create an entity with no components (empty archetype)
    e_empty = w.create_entity()
    assert isinstance(e_empty, int)
    assert w.has_component(e_empty, Position) is False
    assert w.get_component(e_empty, Position) is None

    # Create entities with various component sets
    e1 = w.create_entity([Position(1.0, 2.0)])
    e2 = w.create_entity([Position(3.0, 4.0), Velocity(0.5, -0.5)])
    e3 = w.create_entity([Velocity(1.0, 1.0)])

    # Check has/get component behavior
    assert w.has_component(e1, Position) is True
    assert w.has_component(e1, Velocity) is False
    p1 = w.get_component(e1, Position)
    assert isinstance(p1, Position) and (p1.x, p1.y) == (1.0, 2.0)
    assert w.get_component(e1, Velocity) is None

    assert w.has_component(e2, Position) is True
    assert w.has_component(e2, Velocity) is True
    p2 = w.get_component(e2, Position)
    v2 = w.get_component(e2, Velocity)
    assert isinstance(p2, Position) and (p2.x, p2.y) == (3.0, 4.0)
    assert isinstance(v2, Velocity) and (v2.dx, v2.dy) == (0.5, -0.5)

    assert w.has_component(e3, Position) is False
    assert w.has_component(e3, Velocity) is True
    assert w.get_component(e3, Position) is None

    # Remove Velocity from e2
    w.remove_component(e2, Velocity)
    assert w.has_component(e2, Velocity) is False
    assert w.has_component(e2, Position) is True
    assert isinstance(w.get_component(e2, Position), Position)

    # Destroy e1 and ensure accessors reflect removal
    w.destroy_entity(e1)
    assert w.has_component(e1, Position) is False
    assert w.get_component(e1, Position) is None


def test_queries_and_deterministic_ordering():
    w1 = ECSWorld()

    # Build a small world
    e1 = w1.create_entity([Position(1, 1)])
    e2 = w1.create_entity([Position(2, 2), Velocity(1, 0)])
    e3 = w1.create_entity([Velocity(0, 1)])

    # Basic queries
    sig_pos = QuerySignature(read=(Position,), write=())
    q_pos = w1.query(sig_pos)
    results_pos = list(q_pos)
    # Must be ordered by ascending EntityID
    assert [row.entity for row in results_pos] == sorted([e1, e2])
    # Ensure each has Position and tuple order matches query
    for row in results_pos:
        (p,) = row.components
        assert isinstance(p, Position)

    sig_both = QuerySignature(read=(Position, Velocity), write=())
    q_both = w1.query(sig_both)
    results_both = list(q_both)
    # Only entities with both
    assert [row.entity for row in results_both] == [e2]
    (p2, v2) = results_both[0].components
    assert p2 == w1.get_component(e2, Position)
    assert v2 == w1.get_component(e2, Velocity)

    # Determinism: replay same sequence in a new world and compare
    w2 = ECSWorld()
    e1b = w2.create_entity([Position(1, 1)])
    e2b = w2.create_entity([Position(2, 2), Velocity(1, 0)])
    e3b = w2.create_entity([Velocity(0, 1)])

    assert (e1, e2, e3) == (1, 2, 3)
    assert (e1b, e2b, e3b) == (1, 2, 3)

    # Same queries yield identical entity ordering and component types
    results_pos2 = list(w2.query(sig_pos))
    assert [row.entity for row in results_pos2] == [row.entity for row in results_pos]
    for row in results_pos2:
        (p,) = row.components
        assert isinstance(p, Position)

    results_both2 = list(w2.query(sig_both))
    assert [row.entity for row in results_both2] == [row.entity for row in results_both]
    (p2b, v2b) = results_both2[0].components
    assert isinstance(p2b, Position) and isinstance(v2b, Velocity)
