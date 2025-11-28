# backend/sim4/world/default_layouts.py

from .board_layout import BoardLayoutSpec, ConnectionSpec


def make_default_two_room_layout() -> BoardLayoutSpec:
    """
    Minimal AAA test layout:
    Room A <-> Room B
    """
    return BoardLayoutSpec(
        rooms=["A", "B"],
        connections={
            "A": [ConnectionSpec(to="B", cost=1.0, kind="hallway")],
            "B": [ConnectionSpec(to="A", cost=1.0, kind="hallway")],
        }
    )
