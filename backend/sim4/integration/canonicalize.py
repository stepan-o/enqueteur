from __future__ import annotations

"""Canonicalization and quantization utilities for Sim4 Sprint 14.2.

Rules:
- Deterministic float quantization using Decimal with HALF_UP to 3 decimal places.
- Recursive deep quantization that only touches floats.
- Stable sorting helpers for domain objects (rooms/agents/items/events).
- Convenience canonicalizer for state-like payloads that deep-copies, quantizes,
  and sorts known arrays without inventing fields.

This module contains no IO and no transport/session logic.
"""

from dataclasses import is_dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Iterable, List
import copy


# Quantization constant (Q1E3 = 0.001)
Q1E3: float = 1e-3


def quantize_f(x: float, q: float = Q1E3) -> float:
    """Quantize a float x to the nearest multiple of q using HALF_UP at 3 dp.

    Implementation detail: uses Decimal(str(x)) and Decimal("0.001") with
    ROUND_HALF_UP to avoid binary float rounding surprises.
    """
    # Only support Q1E3 for now; q is accepted for future extension but ignored
    # because we always quantize to 3 decimal places as per sprint spec.
    _ = q  # keep signature while being explicit that 3dp is the policy
    d = Decimal(str(x))
    quantized = d.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return float(quantized)


def _quantize_in_place(obj: Any) -> Any:
    """Internal recursive quantizer for floats only.

    Returns a new structure; does not mutate inputs.
    """
    if isinstance(obj, float):
        return quantize_f(obj)
    if isinstance(obj, (int, str, bool)) or obj is None:
        return obj
    if isinstance(obj, list):
        return [_quantize_in_place(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_quantize_in_place(v) for v in obj)
    if isinstance(obj, dict):
        return {k: _quantize_in_place(v) for k, v in obj.items()}
    # Dataclass support: convert to dict of primitives/containers and recurse
    if is_dataclass(obj):
        return _quantize_in_place(asdict(obj))
    # Fallback: leave as-is (unknown type), caller should stick to primitives
    return obj


def quantize_obj(obj: Any, q: float = Q1E3) -> Any:
    """Deep-quantize floats within obj to 3 decimal places (Q1E3).

    - dict/list/tuple traversed recursively
    - floats quantized; ints left alone
    - strings/bools/None unchanged
    - returns a new object (does not mutate input)
    """
    _ = q
    # Make a deep copy first to emphasize immutability; then quantize copy
    copied = copy.deepcopy(obj)
    return _quantize_in_place(copied)


# --- Stable sorting helpers ---


def sort_by_key(items: List[Any], key_fn: Callable[[Any], Any]) -> List[Any]:
    """Return a new list sorted by key_fn, stable across runs."""
    return sorted(items, key=key_fn)


def sort_in_place(items: List[Any], key_fn: Callable[[Any], Any]) -> None:
    """Sort the list in place by key_fn, stable across runs."""
    items.sort(key=key_fn)


def _get_field(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    # attr fallback (dataclasses/objects)
    return getattr(obj, name, None)


def sort_rooms(rooms: Iterable[Any]) -> List[Any]:
    return sort_by_key(list(rooms), key_fn=lambda r: _get_field(r, "room_id"))


def sort_agents(agents: Iterable[Any]) -> List[Any]:
    return sort_by_key(list(agents), key_fn=lambda a: _get_field(a, "agent_id"))


def sort_items(items: Iterable[Any]) -> List[Any]:
    return sort_by_key(list(items), key_fn=lambda i: _get_field(i, "item_id"))


def sort_objects(objects: Iterable[Any]) -> List[Any]:
    return sort_by_key(list(objects), key_fn=lambda o: _get_field(o, "object_id"))


def sort_events(events: Iterable[Any]) -> List[Any]:
    return sort_by_key(
        list(events), key_fn=lambda e: (_get_field(e, "tick"), _get_field(e, "event_id"))
    )


def canonicalize_state_obj(state_obj: dict) -> dict:
    """Return a canonical deep-copied state object.

    - Deep copy input
    - Quantize all floats
    - If keys exist and are lists, apply known sort rules for rooms/agents/items/events
    - Do not invent fields
    """
    if not isinstance(state_obj, dict):
        raise ValueError("state_obj must be a dict")
    # Deep copy first
    result = copy.deepcopy(state_obj)

    # Quantize floats everywhere
    result = _quantize_in_place(result)

    # Apply domain ordering conservatively if present and list-like
    def _maybe_sort(container: dict, key: str, sorter: Callable[[Iterable[Any]], List[Any]]):
        val = container.get(key)
        if isinstance(val, list):
            container[key] = sorter(val)

    _maybe_sort(result, "rooms", sort_rooms)
    _maybe_sort(result, "agents", sort_agents)
    _maybe_sort(result, "items", sort_items)
    _maybe_sort(result, "objects", sort_objects)
    _maybe_sort(result, "events", sort_events)

    return result


__all__ = [
    "Q1E3",
    "quantize_f",
    "quantize_obj",
    "sort_by_key",
    "sort_in_place",
    "sort_rooms",
    "sort_agents",
    "sort_items",
    "sort_objects",
    "sort_events",
    "canonicalize_state_obj",
]
