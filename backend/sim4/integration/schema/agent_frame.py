from dataclasses import dataclass


@dataclass(frozen=True)
class AgentFrame:
    """Primitives-only agent snapshot for the viewer frame.

    Positions and time are expected to be quantized by the builder.
    """

    agent_id: int
    room_id: int | None
    x: float
    y: float
    action_state_code: int
