from __future__ import annotations

import itertools
import random


def test_determinism_under_shuffled_order():
    from backend.sim4.integration.layout_algos import layout_rooms, RoomIdentityLike

    rooms = [RoomIdentityLike(room_id=rid) for rid in [5, 1, 3, 2, 4]]
    # Simple chain graph 1-2-3-4-5
    nav = {1: [2], 2: [1, 3], 3: [2, 4], 4: [3, 5], 5: [4]}

    base = layout_rooms(rooms, nav, room_width=1.0, room_height=1.0, gap_x=0.5, gap_y=0.5)

    # Shuffle input order multiple times; results must be identical
    for _ in range(5):
        shuffled = list(rooms)
        random.Random(42 + _).shuffle(shuffled)
        out = layout_rooms(shuffled, nav, room_width=1.0, room_height=1.0, gap_x=0.5, gap_y=0.5)
        assert out == base


def test_quantized_coordinates_only():
    from backend.sim4.integration.layout_algos import layout_rooms, RoomIdentityLike
    from backend.sim4.integration.util.quantize import qf

    rooms = [RoomIdentityLike(room_id=i) for i in range(1, 7)]
    out = layout_rooms(rooms, None, room_width=1.234567, room_height=0.987654, gap_x=0.333333, gap_y=0.444444)

    for rid, (x, y, z) in out.items():
        assert qf(x) == x
        assert qf(y) == y
        assert isinstance(z, int)


def test_disconnected_graph_components_non_overlapping_and_ordered():
    from backend.sim4.integration.layout_algos import layout_rooms, RoomIdentityLike

    # Component A: rooms 1,2,3 in a star from 1
    # Component B: rooms 10,11 as a pair
    rooms = [RoomIdentityLike(room_id=r) for r in [1, 2, 3, 10, 11]]
    nav = {
        1: [2, 3],
        2: [1],
        3: [1],
        10: [11],
        11: [10],
    }
    out = layout_rooms(rooms, nav, room_width=2.0, room_height=1.0, gap_x=0.5, gap_y=0.25)

    # Separate by components: A should be to the left of B deterministically
    xs_A = [out[i][0] for i in [1, 2, 3]]
    xs_B = [out[i][0] for i in [10, 11]]
    assert max(xs_A) < min(xs_B), "Components must not overlap horizontally and A must be left of B"

    # z_layer equals BFS depth: root=1 depth=0, its neighbors depth=1
    assert out[1][2] == 0
    assert out[2][2] == 1 and out[3][2] == 1


def test_stability_when_adding_isolated_room_grid_mode():
    from backend.sim4.integration.layout_algos import layout_rooms, RoomIdentityLike

    base_rooms = [RoomIdentityLike(room_id=i) for i in [3, 1, 2, 4]]
    out1 = layout_rooms(base_rooms, None, room_width=1.0, room_height=1.0, gap_x=0.25, gap_y=0.25)

    # Add an isolated room (no navgraph => grid mode)
    extended_rooms = base_rooms + [RoomIdentityLike(room_id=99)]
    out2 = layout_rooms(extended_rooms, None, room_width=1.0, room_height=1.0, gap_x=0.25, gap_y=0.25)

    # Positions of original rooms must be unchanged
    for r in [1, 2, 3, 4]:
        assert out1[r] == out2[r]


def test_identical_output_across_repeated_calls():
    from backend.sim4.integration.layout_algos import layout_rooms, RoomIdentityLike

    rooms = [RoomIdentityLike(room_id=r) for r in [7, 2, 5, 1, 3, 4, 6]]
    nav = {1: [2], 2: [1, 3], 3: [2, 4], 4: [3], 5: [], 6: [], 7: []}

    out_a = layout_rooms(list(rooms), nav, room_width=1.5, room_height=1.0, gap_x=0.5, gap_y=0.5)
    out_b = layout_rooms(list(rooms), nav, room_width=1.5, room_height=1.0, gap_x=0.5, gap_y=0.5)
    assert out_a == out_b
