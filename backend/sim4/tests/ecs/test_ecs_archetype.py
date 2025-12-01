import pytest

from backend.sim4.ecs import (
    ArchetypeSignature,
    ArchetypeRegistry,
)


def test_signature_normalization_and_equality():
    a = ArchetypeSignature.from_type_codes([3, 1, 2])
    b = ArchetypeSignature.from_type_codes([2, 3, 1, 2])
    assert a == b
    # underlying tuple should be sorted and unique
    assert a.component_type_codes == (1, 2, 3)
    assert b.component_type_codes == (1, 2, 3)


def test_signature_is_hashable():
    a = ArchetypeSignature.from_type_codes([10, 5, 5])
    b = ArchetypeSignature.from_type_codes([5, 10])
    s = {a, b}
    # Both normalize to the same signature, so set size is 1
    assert len(s) == 1
    d = {a: "ok"}
    assert d[b] == "ok"


def test_with_and_without_component():
    sig = ArchetypeSignature.from_type_codes([2, 4])
    sig2 = sig.with_component(4)  # already present
    assert sig2 == sig  # logically equal, may even be same object

    sig3 = sig.with_component(3)  # new code
    assert sig3.component_type_codes == (2, 3, 4)

    sig4 = sig3.without_component(3)  # remove previously added
    assert sig4.component_type_codes == (2, 4)

    sig5 = sig4.without_component(999)  # missing code
    assert sig5 == sig4


def test_registry_determinism_and_ordering():
    reg = ArchetypeRegistry()

    s1a = ArchetypeSignature.from_type_codes([3, 1])
    s1b = ArchetypeSignature.from_type_codes([1, 3])  # same as s1a
    s2 = ArchetypeSignature.from_type_codes([2])
    s3 = ArchetypeSignature.from_type_codes([1, 2, 3])

    id1 = reg.get_or_register(s1a)
    id1_again = reg.get_or_register(s1b)
    assert id1 == id1_again == 0  # first seen gets ID 0 (documented)

    id2 = reg.get_or_register(s2)
    assert id2 == 1

    id3 = reg.get_or_register(s3)
    assert id3 == 2

    # get_signature returns equal signatures
    assert reg.get_signature(id1) == s1a == s1b
    assert reg.get_signature(id2) == s2
    assert reg.get_signature(id3) == s3


def test_registry_ensure_signature_and_invalid_lookup():
    reg = ArchetypeRegistry()

    id0 = reg.ensure_signature([5, 4, 5])  # normalizes to (4,5)
    assert id0 == 0
    assert reg.get_signature(id0).component_type_codes == (4, 5)

    # invalid ID should raise IndexError
    with pytest.raises(IndexError):
        reg.get_signature(999)
