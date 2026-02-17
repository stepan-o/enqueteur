from __future__ import annotations

"""KVP state history for offline exports (v0.1).

Collects per-tick snapshots via TickOutputSink and exposes a StateSource
interface for export_state_records(...).
"""

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Sequence

from backend.sim4.snapshot.output import TickOutputSink
from backend.sim4.snapshot.world_snapshot import WorldSnapshot

from .canonicalize import canonicalize_state_obj
from .manifest_schema import ALLOWED_CHANNELS
from .export_state import StateSource
from .step_hash import compute_step_hash


def _to_plain(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return dict(obj)
    try:
        return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_") and not callable(getattr(obj, k))}
    except Exception:
        return obj


def _events_to_state(events: Sequence[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ev in events:
        payload = _to_plain(getattr(ev, "payload", ev))
        tick = getattr(ev, "tick_index", None)
        seq = getattr(ev, "seq", None)
        origin = getattr(ev, "origin", None)
        out.append(
            {
                "tick": int(tick) if tick is not None else 0,
                "event_id": int(seq) if seq is not None else 0,
                "origin": str(origin) if origin is not None else "",
                "payload": payload,
            }
        )
    return out


class KvpStateHistory(TickOutputSink, StateSource):
    """Collects canonical KVP state per tick and serves it to exporter."""

    def __init__(self, *, channels: Sequence[str] | None = None) -> None:
        self._channels = list(channels) if channels is not None else list(ALLOWED_CHANNELS)
        self._channels = sorted({c for c in self._channels if c in ALLOWED_CHANNELS})
        if not self._channels:
            raise ValueError("channels must be a non-empty subset of ALLOWED_CHANNELS")

        self._state_by_tick: Dict[int, Dict[str, Any]] = {}
        self._step_hash_by_tick: Dict[int, str] = {}

    # --- TickOutputSink ---
    def on_tick_output(
        self,
        *,
        tick_index: int,
        dt: float,
        world_snapshot: WorldSnapshot,
        runtime_events: Sequence[Any],
        narrative_fragments: Sequence[Any],
    ) -> None:
        _ = dt
        _ = narrative_fragments

        state: Dict[str, Any] = {}

        if "WORLD" in self._channels:
            state["rooms"] = [_to_plain(r) for r in world_snapshot.rooms]
            state["objects"] = [_to_plain(o) for o in world_snapshot.objects]
            state["world"] = {
                "factory_input": float(world_snapshot.factory_input),
                "day_index": int(world_snapshot.day_index),
                "ticks_per_day": int(world_snapshot.ticks_per_day),
                "tick_in_day": int(world_snapshot.tick_in_day),
                "time_of_day": float(world_snapshot.time_of_day),
                "day_phase": str(world_snapshot.day_phase),
                "phase_progress": float(world_snapshot.phase_progress),
                "doors": [_to_plain(d) for d in world_snapshot.doors],
            }
        if "AGENTS" in self._channels:
            state["agents"] = [_to_plain(a) for a in world_snapshot.agents]
        if "ITEMS" in self._channels:
            state["items"] = [_to_plain(i) for i in world_snapshot.items]
        if "EVENTS" in self._channels:
            state["events"] = _events_to_state(runtime_events)
        if "DEBUG" in self._channels:
            state.setdefault("debug", {})

        canonical_state = canonicalize_state_obj(state)
        step_hash = compute_step_hash(canonical_state)

        self._state_by_tick[int(tick_index)] = canonical_state
        self._step_hash_by_tick[int(tick_index)] = step_hash

    # --- StateSource ---
    def get_state(self, tick: int) -> Dict[str, Any]:  # type: ignore[override]
        if tick not in self._state_by_tick:
            raise KeyError(f"Missing state for tick={tick}")
        return self._state_by_tick[tick]

    # --- Helpers ---
    def get_step_hash(self, tick: int) -> str:
        if tick not in self._step_hash_by_tick:
            raise KeyError(f"Missing step_hash for tick={tick}")
        return self._step_hash_by_tick[tick]

    def ticks(self) -> List[int]:
        return sorted(self._state_by_tick.keys())


__all__ = ["KvpStateHistory"]
