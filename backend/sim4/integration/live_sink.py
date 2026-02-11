from __future__ import annotations

"""LIVE transport sink for KVP-0001 (v0.1).

Consumes runtime Phase H snapshots via TickOutputSink and publishes
FULL_SNAPSHOT / FRAME_DIFF envelopes over a LiveSession.

This is a draft adapter: it assumes a single live subscriber and does not
attempt backpressure or retransmit logic yet.
"""

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, List, Sequence

from backend.sim4.snapshot.output import TickOutputSink
from backend.sim4.snapshot.world_snapshot import WorldSnapshot

from .canonicalize import canonicalize_state_obj
from .schema_version import INTEGRATION_SCHEMA_VERSION
from .step_hash import compute_step_hash
from .diff_ops import compute_state_diff_ops
from .live_session import LiveSession
from .manifest_schema import ALLOWED_CHANNELS


def _to_plain(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return dict(obj)
    # Best-effort attribute dict for simple objects
    try:
        return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_") and not callable(getattr(obj, k))}
    except Exception:
        return obj


def _events_to_state(events: Sequence[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ev in events:
        payload = _to_plain(ev.payload)
        out.append(
            {
                "tick": int(ev.tick_index),
                "event_id": int(ev.seq),
                "origin": str(ev.origin),
                "payload": payload,
            }
        )
    return out


class LiveKvpStateSink(TickOutputSink):
    """Publish KVP state envelopes to a LiveSession.

    Policy:
    - First observed tick emits FULL_SNAPSHOT.
    - Subsequent ticks emit FRAME_DIFF ops[] with prev_step_hash.
    - If tick continuity is broken, emits a new FULL_SNAPSHOT.
    """

    def __init__(
        self,
        session: LiveSession,
        *,
        channels: Sequence[str] | None = None,
    ) -> None:
        self._session = session
        self._channels = list(channels) if channels is not None else list(ALLOWED_CHANNELS)
        # Normalize channel set deterministically
        self._channels = sorted({c for c in self._channels if c in ALLOWED_CHANNELS})
        if not self._channels:
            raise ValueError("channels must be a non-empty subset of ALLOWED_CHANNELS")

        self._has_baseline = False
        self._prev_tick: int | None = None
        self._prev_step_hash: str | None = None
        self._prev_state: Dict[str, Any] | None = None

    def reset_baseline(self) -> None:
        """Reset baseline state (e.g., after a new SUBSCRIBE)."""
        self._has_baseline = False
        self._prev_tick = None
        self._prev_step_hash = None
        self._prev_state = None

    def on_tick_output(
        self,
        *,
        tick_index: int,
        dt: float,
        world_snapshot: WorldSnapshot,
        runtime_events: Sequence[Any],
        narrative_fragments: Sequence[Any],
    ) -> None:
        # Narrative fragments are out-of-protocol in v0.1; ignored here.
        _ = dt
        _ = narrative_fragments

        state: Dict[str, Any] = {}

        if "WORLD" in self._channels:
            state["rooms"] = [_to_plain(r) for r in world_snapshot.rooms]
            state["objects"] = [_to_plain(o) for o in world_snapshot.objects]
            state["world"] = {"factory_input": float(world_snapshot.factory_input)}
        if "AGENTS" in self._channels:
            state["agents"] = [_to_plain(a) for a in world_snapshot.agents]
        if "ITEMS" in self._channels:
            state["items"] = [_to_plain(i) for i in world_snapshot.items]
        if "EVENTS" in self._channels:
            state["events"] = _events_to_state(runtime_events)
        if "DEBUG" in self._channels:
            # Placeholder for future debug fields; keep deterministic
            state.setdefault("debug", {})

        # Canonicalize + hash
        canonical_state = canonicalize_state_obj(state)
        step_hash = compute_step_hash(canonical_state)

        # Decide snapshot vs diff
        if (not self._has_baseline) or (self._prev_tick is None) or (tick_index != self._prev_tick + 1):
            payload = {
                "schema_version": INTEGRATION_SCHEMA_VERSION,
                "tick": int(tick_index),
                "state": canonical_state,
                "step_hash": step_hash,
            }
            self._session.publish_full_snapshot(payload)
            self._has_baseline = True
            self._prev_tick = int(tick_index)
            self._prev_step_hash = step_hash
            self._prev_state = canonical_state
            return

        if self._prev_state is None:
            # Defensive: if baseline state missing, re-send snapshot
            payload = {
                "schema_version": INTEGRATION_SCHEMA_VERSION,
                "tick": int(tick_index),
                "state": canonical_state,
                "step_hash": step_hash,
            }
            self._session.publish_full_snapshot(payload)
            self._has_baseline = True
            self._prev_tick = int(tick_index)
            self._prev_step_hash = step_hash
            self._prev_state = canonical_state
            return

        ops = compute_state_diff_ops(self._prev_state, canonical_state)

        # Diff payload (ops-based)
        payload = {
            "schema_version": INTEGRATION_SCHEMA_VERSION,
            "from_tick": int(self._prev_tick),
            "to_tick": int(tick_index),
            "prev_step_hash": self._prev_step_hash,
            "ops": ops,
            "step_hash": step_hash,
        }
        self._session.publish_frame_diff(payload)
        self._prev_tick = int(tick_index)
        self._prev_step_hash = step_hash
        self._prev_state = canonical_state


__all__ = ["LiveKvpStateSink"]
