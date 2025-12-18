from __future__ import annotations

"""
Runtime → Integration bridge for BubbleEvents (Sub-Sprint 11.2).

Pure mapping from narrative StoryFragment → integration BubbleEvent.

Determinism & Guardrails:
- No I/O, clocks, or RNG.
- Imports only narrative StoryFragment (runtime) and integration.ui_events DTOs.
- Returns events sorted by bubble_event_sort_key.
"""

from typing import List

from backend.sim4.runtime.narrative_context import StoryFragment
from backend.sim4.integration.ui_events import (
    BubbleEvent,
    BubbleKind,
    bubble_event_sort_key,
)


def _importance_to_int(x: float, *, min_v: int = -100, max_v: int = 100) -> int:
    # Deterministic conversion via round then clamp to range
    try:
        v = int(round(float(x)))
    except Exception:
        v = 0
    if v < min_v:
        return min_v
    if v > max_v:
        return max_v
    return v


def _scope_to_kind(scope: str) -> BubbleKind:
    s = (scope or "").lower()
    if s == "agent":
        return BubbleKind.DIALOGUE  # default to DIALOGUE; THOUGHT may be introduced by marker later
    if s == "room":
        return BubbleKind.NARRATION
    if s in {"global", "tick"}:
        return BubbleKind.NARRATION
    return BubbleKind.NARRATION


def story_fragments_to_bubble_events(
    *,
    tick_index: int,
    fragments: List[StoryFragment],
    default_duration_ticks: int = 30,
) -> List[BubbleEvent]:
    """Convert StoryFragments into sorted BubbleEvents deterministically.

    - Filters empty/whitespace texts.
    - Anchors agent/room per scope policy.
    - Converts float importance to clamped int.
    - Sets duration_ticks to provided default (>=1).
    - Emits BubbleKind as stable string value in BubbleEvent.kind.
    - Returns list sorted by bubble_event_sort_key.
    """

    dur = int(default_duration_ticks)
    if dur < 1:
        dur = 1

    out: List[BubbleEvent] = []
    for fr in fragments or []:
        text = (fr.text or "").strip()
        if not text:
            # Explicitly skip empty to avoid raising in DTO validation inside runtime path
            continue

        kind = _scope_to_kind(fr.scope)

        # Anchoring
        agent_id: int | None
        room_id: int | None
        scope_l = (fr.scope or "").lower()
        if scope_l == "agent":
            agent_id = fr.agent_id
            room_id = fr.room_id
        elif scope_l == "room":
            agent_id = None
            room_id = fr.room_id
        elif scope_l in {"global", "tick"}:
            agent_id = None
            room_id = None
        else:
            agent_id = None
            room_id = None

        imp = _importance_to_int(fr.importance)

        ev = BubbleEvent(
            tick_index=int(tick_index),
            duration_ticks=dur,
            agent_id=agent_id,
            room_id=room_id,
            kind=kind.value,
            text=text,
            importance=imp,
        )
        out.append(ev)

    # Deterministic ordering
    out.sort(key=bubble_event_sort_key)
    return out


__all__ = ["story_fragments_to_bubble_events"]
