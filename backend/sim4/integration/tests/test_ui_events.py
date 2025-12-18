from __future__ import annotations

import json
import sys
import types


def test_ui_events_import_has_no_engine_deps():
    # Ensure engine modules are not already loaded
    engine_modules = [
        "backend.sim4.runtime",
        "backend.sim4.world",
        "backend.sim4.snapshot",
        "backend.sim4.narrative",
    ]
    for m in engine_modules:
        sys.modules.pop(m, None)

    import importlib

    importlib.invalidate_caches()
    pkg = importlib.import_module("backend.sim4.integration.ui_events")
    assert isinstance(pkg, types.ModuleType)
    for m in engine_modules:
        assert m not in sys.modules, f"Module {m} imported implicitly by ui_events"


def test_bubble_event_round_trip_json():
    from backend.sim4.integration.ui_events import BubbleEvent, BubbleKind
    from backend.sim4.integration.util.stable_json import stable_json_dumps

    ev = BubbleEvent(
        tick_index=42,
        duration_ticks=3,
        agent_id=7,
        room_id=11,
        kind=BubbleKind.DIALOGUE.value,
        text="Hello there",
        importance=5,
    )

    s = stable_json_dumps(ev)
    data = json.loads(s)

    # All primitives present
    assert data == {
        "tick_index": 42,
        "duration_ticks": 3,
        "agent_id": 7,
        "room_id": 11,
        "kind": "DIALOGUE",
        "text": "Hello there",
        "importance": 5,
    }

    # Recreate and verify fields
    ev2 = BubbleEvent(**data)
    assert ev2 == ev


def test_bubble_event_validation_rules():
    from backend.sim4.integration.ui_events import BubbleEvent, BubbleKind
    import pytest

    # duration must be >= 1
    with pytest.raises(ValueError):
        BubbleEvent(
            tick_index=0,
            duration_ticks=0,
            agent_id=None,
            room_id=None,
            kind=BubbleKind.NARRATION.value,
            text="x",
            importance=0,
        )

    # text must be non-empty
    with pytest.raises(ValueError):
        BubbleEvent(
            tick_index=0,
            duration_ticks=1,
            agent_id=None,
            room_id=None,
            kind=BubbleKind.NARRATION.value,
            text="   ",
            importance=0,
        )

    # kind must be one of enum values
    with pytest.raises(ValueError):
        BubbleEvent(
            tick_index=0,
            duration_ticks=1,
            agent_id=None,
            room_id=None,
            kind="SOMETHING_ELSE",
            text="ok",
            importance=0,
        )


def test_bubble_event_deterministic_ordering():
    from backend.sim4.integration.ui_events import BubbleEvent, BubbleKind, bubble_event_sort_key

    evs = [
        BubbleEvent(0, 2, 1, None, BubbleKind.DIALOGUE.value, "a", 1),
        BubbleEvent(0, 2, 2, None, BubbleKind.THought.value if False else BubbleKind.THOUGHT.value, "b", 1),
        BubbleEvent(0, 2, None, 5, BubbleKind.NARRATION.value, "c", 1),
        BubbleEvent(0, 2, 1, None, BubbleKind.DIALOGUE.value, "d", 2),  # higher importance
        BubbleEvent(1, 2, None, None, BubbleKind.NARRATION.value, "e", 0),
    ]

    # Sort deterministically
    ordered = sorted(evs, key=bubble_event_sort_key)

    # Build expected tuple order
    def norm(v):
        return v if isinstance(v, int) else 2_147_483_647

    tuples = [
        (e.tick_index, -e.importance, norm(e.agent_id), norm(e.room_id)) for e in evs
    ]
    expected_order = sorted(range(len(evs)), key=lambda i: tuples[i])

    assert [evs.index(e) for e in ordered] == expected_order
