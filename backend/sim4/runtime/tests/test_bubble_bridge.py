from __future__ import annotations


def test_story_fragments_mapping_kinds_and_anchors():
    from backend.sim4.runtime.narrative_context import StoryFragment
    from backend.sim4.runtime.bubble_bridge import story_fragments_to_bubble_events
    from backend.sim4.integration.ui_events import BubbleKind

    frags = [
        StoryFragment(scope="agent", agent_id=1, room_id=10, text="Hello", importance=1.2),
        StoryFragment(scope="room", agent_id=None, room_id=20, text="Wind blows", importance=0.4),
        StoryFragment(scope="global", agent_id=None, room_id=None, text="It starts to rain", importance=2.9),
        StoryFragment(scope="tick", agent_id=None, room_id=None, text="A moment passes", importance=-4.2),
        StoryFragment(scope="unknown", agent_id=None, room_id=None, text="Fallback narration", importance=0.0),
    ]

    events = story_fragments_to_bubble_events(tick_index=7, fragments=frags, default_duration_ticks=5)

    # Should produce one event per fragment, ordered by policy
    assert len(events) == 5

    # Check kinds and anchors
    e0 = next(e for e in events if e.text == "Hello")
    assert e0.kind == BubbleKind.DIALOGUE.value
    assert e0.agent_id == 1 and e0.room_id == 10

    e1 = next(e for e in events if e.text == "Wind blows")
    assert e1.kind == BubbleKind.NARRATION.value
    assert e1.agent_id is None and e1.room_id == 20

    e2 = next(e for e in events if e.text == "It starts to rain")
    assert e2.kind == BubbleKind.NARRATION.value
    assert e2.agent_id is None and e2.room_id is None

    e3 = next(e for e in events if e.text == "A moment passes")
    assert e3.kind == BubbleKind.NARRATION.value
    assert e3.agent_id is None and e3.room_id is None

    e4 = next(e for e in events if e.text == "Fallback narration")
    assert e4.kind == BubbleKind.NARRATION.value
    assert e4.agent_id is None and e4.room_id is None

    # Duration and tick applied
    for ev in events:
        assert ev.tick_index == 7
        assert ev.duration_ticks == 5


def test_importance_conversion_and_ordering():
    from backend.sim4.runtime.narrative_context import StoryFragment
    from backend.sim4.runtime.bubble_bridge import story_fragments_to_bubble_events

    frags = [
        StoryFragment(scope="agent", agent_id=1, room_id=10, text="a", importance=0.51),  # → 1
        StoryFragment(scope="agent", agent_id=2, room_id=10, text="b", importance=0.49),  # → 0
        StoryFragment(scope="room", agent_id=None, room_id=9, text="c", importance=10.7),  # → 11
        StoryFragment(scope="global", agent_id=None, room_id=None, text="d", importance=-150.2),  # clamp -100
    ]

    events = story_fragments_to_bubble_events(tick_index=0, fragments=frags)

    # Importance conversion
    imps = {e.text: e.importance for e in events}
    assert imps["a"] == 1
    assert imps["b"] == 0
    assert imps["c"] == 11
    assert imps["d"] == -100

    # Ordering: same tick, sorted by (-importance desc, agent_id asc, room_id asc with None last)
    order = [e.text for e in events]
    assert order[0] == "c"  # highest importance 11


def test_empty_text_is_filtered():
    from backend.sim4.runtime.narrative_context import StoryFragment
    from backend.sim4.runtime.bubble_bridge import story_fragments_to_bubble_events

    frags = [
        StoryFragment(scope="agent", agent_id=1, room_id=1, text="   ", importance=1.0),
        StoryFragment(scope="room", agent_id=None, room_id=2, text="ok", importance=0.0),
        StoryFragment(scope="global", agent_id=None, room_id=None, text="\n\t", importance=0.0),
    ]

    events = story_fragments_to_bubble_events(tick_index=1, fragments=frags)
    texts = [e.text for e in events]
    assert texts == ["ok"], "Only non-empty text fragment should remain"
