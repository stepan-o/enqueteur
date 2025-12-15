from dataclasses import dataclass


@dataclass(frozen=True)
class ItemFrame:
    """Primitives-only item snapshot for the viewer frame.

    Deterministic, Rust-portable.
    """

    item_id: int
    room_id: int | None
    owner_agent_id: int | None
    status_code: int
