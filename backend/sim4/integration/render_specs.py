from __future__ import annotations

"""
Sprint 12.1 — Viewer-facing Render Specifications (contracts only)

This module defines primitives-only DTOs for the viewer to render rooms and
agents. There is no simulation logic, I/O, clocks, or RNG here (SOP-100/200).

Rules:
- All fields are JSON-serializable primitives.
- Floats are quantized via integration.util.quantize.qf at creation time to
  ensure deterministic byte-stable outputs across runs/platforms.
- Enum-like references are expressed as strings only (Rust-portable).

Asset reference naming convention (placeholders):
- Room art refs: "room/default"
- Agent sprite refs: "agent/default"
- These strings are deterministic and purely symbolic; no filesystem access.
"""

from dataclasses import dataclass

from .util.quantize import qf


@dataclass(frozen=True)
class RoomRenderSpec:
    room_id: int | str
    world_x: float
    world_y: float
    width: float
    height: float
    z_layer: int
    art_ref: str

    def __post_init__(self) -> None:
        # Quantize float fields deterministically
        object.__setattr__(self, "world_x", qf(float(self.world_x)))
        object.__setattr__(self, "world_y", qf(float(self.world_y)))
        object.__setattr__(self, "width", qf(float(self.width)))
        object.__setattr__(self, "height", qf(float(self.height)))
        # Normalize ids to primitives
        rid = self.room_id
        if isinstance(rid, bool):  # avoid bool subclass of int surprises
            rid = int(rid)
        object.__setattr__(self, "room_id", rid if isinstance(rid, str) else int(rid))


@dataclass(frozen=True)
class AgentRenderSpec:
    agent_id: int | str
    sprite_ref: str
    bubble_anchor_dx: float
    bubble_anchor_dy: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "bubble_anchor_dx", qf(float(self.bubble_anchor_dx)))
        object.__setattr__(self, "bubble_anchor_dy", qf(float(self.bubble_anchor_dy)))
        aid = self.agent_id
        if isinstance(aid, bool):
            aid = int(aid)
        object.__setattr__(self, "agent_id", aid if isinstance(aid, str) else int(aid))


@dataclass(frozen=True)
class AssetPackManifest:
    """Placeholder asset references for viewer rendering.

    Strings only; no validation or filesystem access. Defaults are deterministic.
    """

    # Placeholders
    default_room_art_ref: str = "room/default"
    default_agent_sprite_ref: str = "agent/default"

    # Default bubble anchor (relative to agent sprite origin) for thought/dialogue
    default_bubble_anchor_dx: float = 0.0
    default_bubble_anchor_dy: float = -1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "default_bubble_anchor_dx", qf(float(self.default_bubble_anchor_dx)))
        object.__setattr__(self, "default_bubble_anchor_dy", qf(float(self.default_bubble_anchor_dy)))


# Deterministic, module-level default asset manifest
DEFAULT_ASSETS = AssetPackManifest()


__all__ = [
    "RoomRenderSpec",
    "AgentRenderSpec",
    "AssetPackManifest",
    "DEFAULT_ASSETS",
]
