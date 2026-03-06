"""Agent stats substrate component (Sprint 17.1).

Numeric-only, Rust-portable fields for agent wellbeing, traits, and economy.
All stats except money are intended to live in [0, 1] and are clamped by systems.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentStats:
    """Core agent stats (simulation-facing)."""

    durability: float
    energy: float
    money: float
    smartness: float
    toughness: float
    obedience: float
    mission_alignment: float


__all__ = ["AgentStats"]
