from dataclasses import dataclass


@dataclass(frozen=True)
class RoomFrame:
    """Primitives-only room snapshot for the viewer frame.

    Deterministic, Rust-portable. Lists must be pre-sorted by the builder.
    """

    room_id: int
    label: str
    neighbors: list[int]
