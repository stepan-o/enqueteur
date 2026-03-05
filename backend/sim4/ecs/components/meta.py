"""Meta/debug substrate components (Sprint 3.5).

Debug-only flags and markers. Not gameplay or narrative state. Numeric/ID-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DebugFlags:
    """
    Debug flags for visualization and tooling only.

    - log_agent: if True, extra logging for this agent.
    - highlight_in_snapshot: if True, highlight in debug UIs.
    - freeze_movement: if True, movement systems should treat this agent as frozen.
    """

    log_agent: bool
    highlight_in_snapshot: bool
    freeze_movement: bool


@dataclass
class SystemMarkers:
    """
    System/debug markers (non-gameplay).

    - archetype_code: small int used for archetype/debug classification.
    - debug_notes_id: optional reference into an external debug text store.
    """

    archetype_code: int
    debug_notes_id: Optional[int]
