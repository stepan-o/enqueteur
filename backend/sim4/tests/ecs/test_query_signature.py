from __future__ import annotations

from dataclasses import dataclass

from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.query import QuerySignature, QueryResult


# --- Dummy components for focused query-engine tests ---
@dataclass
class CompA:
    a: int


@dataclass
class CompB:
    b: int


@dataclass
class CompC:
    c: int


@dataclass
class CompD:
    d: int


@dataclass
class CompE:
    e: int


def test_query_signature_shape() -> None:
    sig = QuerySignature(
        read=(CompA, CompB),
        write=(CompC,),
        optional=(CompD,),
        without=(CompE,),
    )
    assert sig.read == (CompA, CompB)
    assert sig.write == (CompC,)
    assert sig.optional == (CompD,)
    assert sig.without == (CompE,)


def test_basic_query_and_types() -> None:
    world = ECSWorld()
    e1 = world.create_entity([CompA(1)])
    e2 = world.create_entity([CompA(2), CompB(20)])
    _e3 = world.create_entity([CompB(30)])

    sig = QuerySignature(read=(CompA,), write=())
    result = world.query(sig)

    assert isinstance(result, QueryResult)
    rows = list(result)
    assert len(rows) == 2
    # Entities with CompA only: e1 and e2
    entities = [row.entity for row in rows]
    assert set(entities) == {e1, e2}
    # Component tuple length equals number of read+write+optional types (1 here)
    for row in rows:
        assert len(row.components) == 1
        (a,) = row.components
        assert isinstance(a, CompA)


def test_deterministic_ordering() -> None:
    world = ECSWorld()
    e1 = world.create_entity([CompA(1)])
    e2 = world.create_entity([CompA(2)])

    sig = QuerySignature(read=(CompA,), write=())
    result1 = list(world.query(sig))
    result2 = list(world.query(sig))

    ent1 = [row.entity for row in result1]
    ent2 = [row.entity for row in result2]
    assert ent1 == ent2 == sorted([e1, e2])


def test_without_filtering_excludes_entities() -> None:
    world = ECSWorld()
    e1 = world.create_entity([CompA(1)])
    _e2 = world.create_entity([CompA(2), CompE(99)])

    sig = QuerySignature(read=(CompA,), write=(), without=(CompE,))
    rows = list(world.query(sig))
    entities = [row.entity for row in rows]
    # Only e1 should remain since e2 has CompE which is excluded
    assert entities == [e1]


def test_optional_components_present_and_missing() -> None:
    world = ECSWorld()
    e1 = world.create_entity([CompA(1), CompD(10)])
    e2 = world.create_entity([CompA(2)])

    sig = QuerySignature(read=(CompA,), write=(), optional=(CompD,))
    rows = list(world.query(sig))

    # Both entities should appear; components length is read(1) + write(0) + optional(1) = 2
    assert {row.entity for row in rows} == {e1, e2}
    for row in rows:
        assert len(row.components) == 2
        a, d_opt = row.components
        assert isinstance(a, CompA)
        if row.entity == e1:
            assert isinstance(d_opt, CompD)
        elif row.entity == e2:
            assert d_opt is None
