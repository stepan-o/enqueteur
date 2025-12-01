"""Drive vector substrate component (Sprint 3.1).

Mind layer mapping: primarily L4 (drives / motivational substrate).
All fields are numeric and updated by systems; ECS stores only numbers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DriveState:
    """
    Drive vector substrate (L4).

    All values are numeric and clamped/updated by systems.
    This is the core fuel for motive formation.
    """

    curiosity: float
    safety_drive: float
    dominance_drive: float
    meaning_drive: float
    attachment_drive: float
    novelty_drive: float
    fatigue: float
    comfort: float
