import math
import pytest

from backend.sim4.integration.canonicalize import (
    quantize_f,
    sort_rooms,
    sort_agents,
    sort_items,
    sort_events,
    canonicalize_state_obj,
)
from backend.sim4.integration.jcs import canonical_json_bytes
from backend.sim4.integration.step_hash import compute_step_hash


# --- Quantization tests ---


def test_quantize_half_up_positive_edges():
    assert quantize_f(1.23456) == 1.235
    assert quantize_f(1.23444) == 1.234


def test_quantize_half_up_negative_edge():
    # half-up away from zero behavior should produce -1.235
    assert quantize_f(-1.2345) == -1.235


def test_quantize_int_like_float():
    assert quantize_f(2.0) == 2.0


# --- Ordering tests ---


def test_ordering_helpers_domain_lists():
    rooms = [{"room_id": "b"}, {"room_id": "a"}]
    agents = [{"agent_id": "z"}, {"agent_id": "a"}]
    items = [{"item_id": "m"}, {"item_id": "k"}]
    events = [
        {"event_id": "b", "tick": 2},
        {"event_id": "a", "tick": 2},
        {"event_id": "c", "tick": 1},
    ]

    assert [r["room_id"] for r in sort_rooms(rooms)] == ["a", "b"]
    assert [a["agent_id"] for a in sort_agents(agents)] == ["a", "z"]
    assert [i["item_id"] for i in sort_items(items)] == ["k", "m"]
    ev_sorted = sort_events(events)
    assert [(e["tick"], e["event_id"]) for e in ev_sorted] == [
        (1, "c"),
        (2, "a"),
        (2, "b"),
    ]


# --- Canonical bytes determinism tests ---


def test_canonical_json_bytes_key_order_independent():
    a = {"x": 1, "a": 2}
    b = {"a": 2, "x": 1}
    assert canonical_json_bytes(a) == canonical_json_bytes(b)


def test_canonicalize_state_obj_produces_stable_bytes():
    state1 = {
        "rooms": [{"room_id": "b"}, {"room_id": "a"}],
        "pos": {"x": 1.23456, "y": 2.0},
    }
    state2 = {
        "pos": {"y": 2.0000, "x": 1.23456},
        "rooms": [{"room_id": "a"}, {"room_id": "b"}],
    }

    can1 = canonicalize_state_obj(state1)
    can2 = canonicalize_state_obj(state2)
    b1 = canonical_json_bytes(can1)
    b2 = canonical_json_bytes(can2)
    assert b1 == b2


def test_reject_non_finite_numbers():
    with pytest.raises(ValueError):
        canonical_json_bytes({"x": float("nan")})
    with pytest.raises(ValueError):
        canonical_json_bytes({"x": float("inf")})
    with pytest.raises(ValueError):
        canonical_json_bytes({"x": -float("inf")})


# --- Step hash stability tests ---


def test_step_hash_identical_for_same_object():
    obj = {"a": 1, "b": [1, 2, 3]}
    h1 = compute_step_hash(obj)
    h2 = compute_step_hash(obj)
    assert h1 == h2


def test_step_hash_identical_for_semantically_equal_after_canonicalization():
    # Different key order and float precision before quantize
    s1 = {"rooms": [{"room_id": "2"}, {"room_id": "1"}], "v": 1.23456}
    s2 = {"v": 1.2345600, "rooms": [{"room_id": "1"}, {"room_id": "2"}]}
    can1 = canonicalize_state_obj(s1)
    can2 = canonicalize_state_obj(s2)
    h1 = compute_step_hash(can1)
    h2 = compute_step_hash(can2)
    assert h1 == h2
