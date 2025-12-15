from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from ..schema.tick_frame import TickFrame
from ..schema.version import IntegrationSchemaVersion
from ..util.stable_hash import stable_hash

if TYPE_CHECKING:
    from backend.sim4.snapshot.world_snapshot import WorldSnapshot
    from backend.sim4.snapshot.episode_types import EpisodeNarrativeFragment
def _to_plain(obj: Any) -> dict:
    """Convert a DTO-like object into a plain dict deterministically.

    - If already a dict (or Mapping), return a new dict with the same items.
    - If a dataclass, use asdict (which is deterministic for frozen/simple trees).
    - Otherwise, reflect public attributes (non-callable, no underscore prefix).
    """
    if isinstance(obj, Mapping):
        return dict(obj)
    if is_dataclass(obj):
        return asdict(obj)
    # Fallback: gather public attributes
    out: dict[str, Any] = {}
    for k in dir(obj):
        if k.startswith("_"):
            continue
        try:
            v = getattr(obj, k)
        except Exception:
            continue
        if callable(v):
            continue
        out[k] = v
    return out


def _event_sort_key(e_dict: Mapping[str, Any]) -> tuple:
    # Prefer explicit tick fields; fall back to current frame tick set later.
    event_tick = e_dict.get("tick")
    if event_tick is None:
        event_tick = e_dict.get("tick_index")
    kind = e_dict.get("kind") or e_dict.get("type") or e_dict.get("name") or ""
    # Stable tiebreaker by payload hash
    payload_hash = stable_hash(e_dict)
    return (int(event_tick) if isinstance(event_tick, (int, float)) and event_tick is not None else -1, str(kind), payload_hash)


def _narr_sort_key(n_dict: Mapping[str, Any]) -> tuple:
    t = n_dict.get("tick")
    if t is None:
        t = n_dict.get("tick_index")
    # Higher importance first; default 0
    importance = n_dict.get("importance", 0)
    # Use negatives for DESC sort by using tuple with -importance (but we'll sort ascending)
    agent_id = n_dict.get("agent_id")
    room_id = n_dict.get("room_id")
    return (
        int(t) if isinstance(t, (int, float)) and t is not None else -1,
        -int(importance) if isinstance(importance, (int, float)) else 0,
        int(agent_id) if isinstance(agent_id, (int, float)) else (agent_id or 0),
        int(room_id) if isinstance(room_id, (int, float)) else (room_id or 0),
    )


def build_tick_frame(
    world_snapshot: "WorldSnapshot",
    recent_events: Sequence[Any],
    narrative_fragments: Sequence[Any] | None = None,
    *,
    schema_version: IntegrationSchemaVersion | None = None,
    run_id: int | None = None,
) -> TickFrame:
    """Pure adapter converting engine DTOs into a viewer-facing TickFrame.

    - No clocks, RNG, or I/O. Pure transformation of provided inputs.
    - Deterministic ordering of events and narrative fragments.
    - Imports engine types only under TYPE_CHECKING to avoid coupling.
    """
    # Pull canonical tick_index and time from the snapshot deterministically.
    tick_index = getattr(world_snapshot, "tick_index")
    time_seconds = getattr(world_snapshot, "time_seconds", 0.0)
    episode_id = getattr(world_snapshot, "episode_id", None)

    # Normalize inputs to plain dicts
    ev_dicts = [_to_plain(e) for e in (recent_events or [])]
    narr_dicts = [_to_plain(n) for n in (narrative_fragments or [])]

    # Fill missing tick fields in events with current tick for sorting consistency
    filled_events: list[dict] = []
    for d in ev_dicts:
        if "tick" not in d and "tick_index" not in d:
            d = dict(d)
            d["tick_index"] = tick_index
        filled_events.append(d)

    # Deterministic sort
    filled_events.sort(key=_event_sort_key)
    narr_dicts.sort(key=_narr_sort_key)

    # Default schema version if not provided
    if schema_version is None:
        schema_version = IntegrationSchemaVersion(1, 0, 0)

    return TickFrame(
        schema_version=schema_version,
        run_id=run_id,
        episode_id=episode_id,
        tick_index=int(tick_index),
        time_seconds=float(time_seconds),
        world_snapshot=world_snapshot,  # DTO object; type-only import avoids coupling
        events=filled_events,
        narrative_fragments=narr_dicts,
    )
