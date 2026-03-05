"""Narrative handle substrate components (Sprint 3.5).

L6/L7 narrative state handle. Only the narrative layer (via adapters)
may mutate this component; ECS systems treat it as read-only metadata.
No free-text is stored here — only numeric IDs and counters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class NarrativeState:
    """
    Narrative state substrate (L6/L7 handle).

    - narrative_id: hashed identifier of an ongoing narrative arc.
    - last_reflection_tick: last tick when narrative reflection occurred.
    - cached_summary_ref: optional ID into an external semantic store.
    - tokens_used_recently: numeric budget tracker for narrative token usage.

    NOTE: Only the narrative layer (via adapters) may mutate this component.
    ECS systems treat it as read-only metadata.
    """

    narrative_id: int
    last_reflection_tick: int
    cached_summary_ref: Optional[int]
    tokens_used_recently: int
