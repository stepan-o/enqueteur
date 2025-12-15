import sys
import types
from copy import deepcopy

import pytest


def make_snapshot(tick_index=10, time_seconds=5.0, episode_id=123):
    class DummySnapshot:
        __slots__ = ("tick_index", "time_seconds", "episode_id")

        def __init__(self):
            self.tick_index = tick_index
            self.time_seconds = time_seconds
            self.episode_id = episode_id

    return DummySnapshot()


def test_build_tick_frame_deterministic_and_sorted():
    # Import locally to avoid polluting sys.modules for the decoupling test
    from backend.sim4.integration.adapters import build_tick_frame

    snapshot = make_snapshot(tick_index=42, time_seconds=21.0, episode_id=7)

    # Events with mixed structure and shuffled order; some missing tick
    events = [
        {"kind": "move", "agent_id": 2, "tick_index": 41, "dx": 1},
        {"kind": "move", "agent_id": 1, "dx": 1},  # no tick -> current
        {"type": "speak", "agent_id": 2, "text": "Hello"},
        {"name": "pickup", "agent_id": 1, "item_id": 99, "tick": 42},
    ]

    # Narrative fragments with mixed importance, tick, and ids
    narr = [
        {"tick_index": 42, "importance": 1, "agent_id": 2, "room_id": 10, "text": "Hi"},
        {"tick": 41, "importance": 5, "agent_id": 1, "room_id": 9, "text": "Earlier"},
        {"importance": 3, "agent_id": 1, "room_id": 9, "text": "Now"},  # tick -> current
    ]

    # Shuffle input orders by reversing copies to simulate non-deterministic source ordering
    events_shuffled = list(reversed(events))
    narr_shuffled = list(reversed(narr))

    frame_a = build_tick_frame(snapshot, events_shuffled, narr_shuffled)
    frame_b = build_tick_frame(snapshot, deepcopy(events_shuffled), deepcopy(narr_shuffled))

    # Same inputs twice -> identical frames
    assert frame_a == frame_b

    # Deterministic contents
    # Events should be sorted by (event_tick, kind/type/name, stable_payload_hash)
    # Check non-decreasing tick order first
    event_ticks = [e.get("tick", e.get("tick_index")) for e in frame_a.events]
    assert event_ticks == sorted(event_ticks)

    # Narrative fragments sorted by (tick, importance DESC, agent_id, room_id)
    narr_keys = [
        (
            d.get("tick", d.get("tick_index")),
            d.get("importance", 0),
            d.get("agent_id"),
            d.get("room_id"),
        )
        for d in frame_a.narrative_fragments
    ]
    # importance should be non-increasing within same tick
    for i in range(1, len(narr_keys)):
        prev, curr = narr_keys[i - 1], narr_keys[i]
        if prev[0] == curr[0]:
            assert prev[1] >= curr[1]


def test_integration_import_does_not_pull_engine_modules():
    # Ensure engine modules are not already loaded
    engine_modules = [
        "backend.sim4.runtime",
        "backend.sim4.world",
        "backend.sim4.snapshot",
        "backend.sim4.narrative",
    ]
    for m in engine_modules:
        sys.modules.pop(m, None)

    # Import integration package
    import importlib

    importlib.invalidate_caches()
    integration_pkg = importlib.import_module("backend.sim4.integration")

    assert isinstance(integration_pkg, types.ModuleType)

    # After import, engine modules should still not be imported implicitly
    for m in engine_modules:
        assert m not in sys.modules, f"Module {m} was imported implicitly by integration"
