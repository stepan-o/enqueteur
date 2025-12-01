import pytest

from backend.sim4.ecs import EntityAllocator, EntityID


def test_monotonic_allocation():
    alloc = EntityAllocator()
    ids = [alloc.allocate() for _ in range(5)]
    assert ids == [1, 2, 3, 4, 5]


def test_alive_tracking():
    alloc = EntityAllocator()
    ids = [alloc.allocate() for _ in range(4)]
    for eid in ids:
        assert alloc.is_alive(eid) is True
    assert alloc.is_alive(9999) is False


def test_destroy_semantics():
    alloc = EntityAllocator()
    e1 = alloc.allocate()
    e2 = alloc.allocate()
    e3 = alloc.allocate()

    assert (e1, e2, e3) == (1, 2, 3)

    # Destroy middle one
    alloc.destroy(e2)
    assert alloc.is_alive(e2) is False
    assert alloc.is_alive(e1) is True
    assert alloc.is_alive(e3) is True

    # Deterministic no-op on repeated destroy
    alloc.destroy(e2)

    # Alive IDs should be sorted and exclude destroyed ID
    assert list(alloc.alive_ids()) == [e1, e3]


def test_no_id_reuse():
    alloc = EntityAllocator()
    ids = [alloc.allocate() for _ in range(3)]
    assert ids == [1, 2, 3]
    alloc.destroy(3)
    nxt = alloc.allocate()
    assert nxt == 4  # not reusing 3


def test_determinism_across_instances():
    a = EntityAllocator()
    b = EntityAllocator()

    # identical sequence
    seq_a = [a.allocate() for _ in range(3)]
    seq_b = [b.allocate() for _ in range(3)]
    assert seq_a == seq_b == [1, 2, 3]

    a.destroy(2)
    b.destroy(2)

    nxt_a = a.allocate()
    nxt_b = b.allocate()

    assert nxt_a == nxt_b == 4
    assert list(a.alive_ids()) == list(b.alive_ids()) == [1, 3, 4]
