import pytest

from backend.sim4.ecs import ArchetypeSignature, ArchetypeStorage, EntityID


def make_storage(type_codes):
    sig = ArchetypeSignature.from_type_codes(type_codes)
    st = ArchetypeStorage(sig, type_codes)
    # Ensure component_type_codes normalized and columns initialized
    assert st.component_type_codes == sorted(list(set(int(t) for t in type_codes)))
    for tc in st.component_type_codes:
        assert tc in st.columns
        assert st.columns[tc] == []
    return st


def test_basic_add_and_column_alignment():
    st = make_storage([1, 2])

    row0 = st.add_entity(EntityID(1), {1: "A1", 2: "B1"})
    row1 = st.add_entity(EntityID(2), {1: "A2"})  # code 2 defaults to None
    row2 = st.add_entity(EntityID(3), {2: "B3"})  # code 1 defaults to None

    assert (row0, row1, row2) == (0, 1, 2)
    assert st.entity_ids == [1, 2, 3]

    # Columns must align with entity_ids length
    assert len(st.columns[1]) == len(st.entity_ids)
    assert len(st.columns[2]) == len(st.entity_ids)

    assert st.columns[1] == ["A1", "A2", None]
    assert st.columns[2] == ["B1", None, "B3"]


def test_remove_middle_swap_remove_and_index_update():
    st = make_storage([1, 2])
    st.add_entity(1, {1: "A1", 2: "B1"})
    st.add_entity(2, {1: "A2"})
    st.add_entity(3, {2: "B3"})

    # Remove entity 2 (middle row index 1)
    removed = st.remove_entity(2)

    # Removed dict reflects prior values
    assert removed == {1: "A2", 2: None}

    # Now two entities remain
    assert st.entity_ids == [1, 3]

    # Entity 3 should now be at row index 1
    assert st.get_row_index(3) == 1
    assert st.columns[1] == ["A1", None]  # 3 had None for comp 1
    assert st.columns[2] == ["B1", "B3"]


def test_remove_last_then_empty():
    st = make_storage([1, 2])
    st.add_entity(1, {1: "A1", 2: "B1"})
    st.add_entity(2, {1: "A2"})

    st.remove_entity(2)  # remove last entity

    assert st.entity_ids == [1]
    assert st.columns[1] == ["A1"]
    assert st.columns[2] == ["B1"]

    st.remove_entity(1)
    assert st.entity_ids == []
    assert st.columns[1] == []
    assert st.columns[2] == []


def test_error_behavior_and_accessors():
    st = make_storage([1, 2])
    st.add_entity(1, {1: "A1", 2: "B1"})

    # Duplicate add should error
    with pytest.raises(ValueError):
        st.add_entity(1, {})

    # Access existing
    assert st.has_entity(1)
    assert st.get_row_index(1) == 0
    assert st.get_component_for_entity(1, 1) == "A1"
    assert st.get_component_for_entity(1, 2) == "B1"

    # Set component
    st.set_component_for_entity(1, 1, "A1x")
    assert st.get_component_for_entity(1, 1) == "A1x"

    # Missing entity
    with pytest.raises(KeyError):
        st.get_row_index(999)

    # Missing component code
    with pytest.raises(KeyError):
        st.get_component_for_entity(1, 999)

    # Remove non-existent
    with pytest.raises(KeyError):
        st.remove_entity(999)


def test_iter_rows_and_determinism():
    # Build a sequence and replay it to ensure same final state
    seq = []

    def run_sequence():
        st = make_storage([1, 2])
        st.add_entity(1, {1: "A1", 2: "B1"})
        st.add_entity(2, {1: "A2"})
        st.add_entity(3, {2: "B3"})
        seq_removed = st.remove_entity(2)
        return st, seq_removed

    a, removed_a = run_sequence()
    b, removed_b = run_sequence()

    assert removed_a == removed_b == {1: "A2", 2: None}

    # Final structures must match exactly
    assert a.entity_ids == b.entity_ids == [1, 3]
    assert a.entity_index == b.entity_index == {1: 0, 3: 1}
    for tc in a.component_type_codes:
        assert a.columns[tc] == b.columns[tc]

    # iter_rows deterministic
    rows = list(a.iter_rows())
    assert rows == [
        (1, {1: "A1", 2: "B1"}),
        (3, {1: None, 2: "B3"}),
    ]
