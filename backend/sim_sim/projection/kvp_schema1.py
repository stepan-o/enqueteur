from __future__ import annotations

"""Project sim_sim domain state to KVP sim_sim_1 viewer state."""

from typing import Any, Dict, List, Mapping, Sequence

from backend.sim4.integration.canonicalize import canonicalize_state_obj
from backend.sim4.integration.manifest_schema import ALLOWED_CHANNELS
from backend.sim4.integration.step_hash import compute_step_hash

from backend.sim_sim.kernel.state import ROOM_IDS, RESOURCE_KEYS, SimSimState


ROOM_BOUNDS: Dict[int, Dict[str, float]] = {
    1: {"min_x": 0.0, "min_y": 0.0, "max_x": 12.0, "max_y": 8.0},
    2: {"min_x": 12.0, "min_y": 0.0, "max_x": 24.0, "max_y": 8.0},
    3: {"min_x": 24.0, "min_y": 0.0, "max_x": 36.0, "max_y": 8.0},
    4: {"min_x": 0.0, "min_y": 8.0, "max_x": 12.0, "max_y": 16.0},
    5: {"min_x": 12.0, "min_y": 8.0, "max_x": 24.0, "max_y": 16.0},
    6: {"min_x": 24.0, "min_y": 8.0, "max_x": 36.0, "max_y": 16.0},
}

ROOM_NEIGHBORS: Dict[int, List[int]] = {
    1: [2, 4],
    2: [1, 3, 5],
    3: [2, 6],
    4: [1, 5],
    5: [2, 4, 6],
    6: [3, 5],
}

SIM_SIM_SCHEMA_VERSION = "sim_sim_1"


def normalize_channels(channels: Sequence[str] | None) -> List[str]:
    if channels is None:
        return list(ALLOWED_CHANNELS)
    out = sorted({c for c in channels if c in ALLOWED_CHANNELS})
    if not out:
        raise ValueError("channels must be a non-empty subset of ALLOWED_CHANNELS")
    return out


def project_state_schema1(
    domain_state: SimSimState,
    channels: Sequence[str],
    *,
    run_context: Mapping[str, Any],
) -> Dict[str, Any]:
    channels_norm = normalize_channels(channels)
    state: Dict[str, Any] = {}

    if "WORLD" in channels_norm:
        state["world_meta"] = _project_world_meta(domain_state, run_context=run_context)
        state["rooms"] = _project_rooms(domain_state)
        state["regime"] = _project_regime(domain_state)

    if "AGENTS" in channels_norm:
        state["supervisors"] = _project_supervisors(domain_state)

    if "ITEMS" in channels_norm:
        state["inventory"] = _project_inventory(domain_state)

    if "EVENTS" in channels_norm:
        state["events"] = _project_events(domain_state)

    if "DEBUG" in channels_norm:
        state["debug"] = {
            "sim_mode": "sim_sim_day_loop",
        }

    return canonicalize_state_obj(state)


def make_snapshot_payload(
    *,
    tick: int,
    domain_state: SimSimState,
    channels: Sequence[str],
    run_context: Mapping[str, Any],
) -> Dict[str, Any]:
    state = project_state_schema1(domain_state, channels, run_context=run_context)
    step_hash = compute_step_hash(state)
    return {
        "schema_version": SIM_SIM_SCHEMA_VERSION,
        "tick": int(tick),
        "state": state,
        "step_hash": step_hash,
    }


def make_diff_payload(
    *,
    from_tick: int,
    to_tick: int,
    previous_state: SimSimState,
    next_state: SimSimState,
    prev_step_hash: str,
    channels: Sequence[str],
    run_context: Mapping[str, Any],
) -> Dict[str, Any]:
    if int(to_tick) != int(from_tick) + 1:
        raise ValueError("to_tick must equal from_tick + 1")

    can_from = project_state_schema1(previous_state, channels, run_context=run_context)
    can_to = project_state_schema1(next_state, channels, run_context=run_context)

    payload: Dict[str, Any] = {
        "schema_version": SIM_SIM_SCHEMA_VERSION,
        "from_tick": int(from_tick),
        "to_tick": int(to_tick),
        "prev_step_hash": str(prev_step_hash),
    }

    if can_to.get("world_meta") != can_from.get("world_meta") and "world_meta" in can_to:
        payload["world_meta_update"] = can_to["world_meta"]
    if can_to.get("regime") != can_from.get("regime") and "regime" in can_to:
        payload["regime_update"] = can_to["regime"]
    if can_to.get("inventory") != can_from.get("inventory") and "inventory" in can_to:
        payload["inventory_update"] = can_to["inventory"]

    room_updates = _diff_by_key(
        from_items=can_from.get("rooms", []),
        to_items=can_to.get("rooms", []),
        key_field="room_id",
    )
    if room_updates:
        payload["room_updates"] = room_updates

    supervisor_updates = _diff_by_key(
        from_items=can_from.get("supervisors", []),
        to_items=can_to.get("supervisors", []),
        key_field="code",
    )
    if supervisor_updates:
        payload["supervisor_updates"] = supervisor_updates

    events_append = _diff_events_append(
        from_events=can_from.get("events", []),
        to_events=can_to.get("events", []),
    )
    if events_append:
        payload["events_append"] = events_append

    step_hash = compute_step_hash(can_to)
    payload["step_hash"] = step_hash
    return payload


def compute_step_hash_for_channels(
    domain_state: SimSimState,
    channels: Sequence[str],
    *,
    run_context: Mapping[str, Any],
) -> str:
    projected = project_state_schema1(domain_state, channels, run_context=run_context)
    return compute_step_hash(projected)


def _project_rooms(domain_state: SimSimState) -> List[Dict[str, Any]]:
    rooms: List[Dict[str, Any]] = []
    for room_id in ROOM_IDS:
        room = domain_state.rooms[room_id]
        rooms.append(
            {
                "room_id": int(room.room_id),
                "name": str(room.name),
                "locked": bool(room.locked),
                "supervisor": room.supervisor,
                "workers_assigned": {
                    "dumb": int(room.workers_assigned_dumb),
                    "smart": int(room.workers_assigned_smart),
                },
                "workers_present": {
                    "dumb": int(room.workers_present_dumb),
                    "smart": int(room.workers_present_smart),
                },
                "equipment_condition": float(room.equipment_condition),
                "stress": float(room.stress),
                "discipline": float(room.discipline),
                "alignment": float(room.alignment),
                "output_today": {key: int(room.output_today.get(key, 0)) for key in RESOURCE_KEYS},
                "accidents_today": {
                    "count": int(room.accidents_count),
                    "casualties": int(room.casualties),
                },
                "bounds": dict(ROOM_BOUNDS[room_id]),
                "neighbors": list(ROOM_NEIGHBORS.get(room_id, [])),
            }
        )
    return rooms


def _project_supervisors(domain_state: SimSimState) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for code in sorted(domain_state.supervisors.keys()):
        supervisor = domain_state.supervisors[code]
        out.append(
            {
                "code": supervisor.code,
                "assigned_room": supervisor.assigned_room,
                "loyalty": float(supervisor.loyalty),
                "confidence": float(supervisor.confidence),
                "influence": float(supervisor.influence),
                "cooldown_days": int(supervisor.cooldown_days),
            }
        )
    return out


def _project_world_meta(domain_state: SimSimState, *, run_context: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "day": int(domain_state.day_tick),
        "phase": str(domain_state.phase),
        "time": str(domain_state.time_label),
        "tick_hz": int(run_context.get("tick_hz", 1)),
        "seed": int(run_context.get("seed", 0)),
        "run_id": str(run_context.get("run_id", "")),
        "world_id": str(run_context.get("world_id", "")),
        "security_lead": str(domain_state.security_lead),
    }


def _project_inventory(domain_state: SimSimState) -> Dict[str, Any]:
    return {
        "cash": int(domain_state.inventory.cash),
        "inventories": {key: int(domain_state.inventory.inventories.get(key, 0)) for key in RESOURCE_KEYS},
    }


def _project_regime(domain_state: SimSimState) -> Dict[str, Any]:
    regime = domain_state.regime
    return {
        "refactor_days": int(regime.refactor_days),
        "inversion_days": int(regime.inversion_days),
        "shutdown_except_brewery_today": bool(regime.shutdown_except_brewery_today),
        "weaving_boost_next_day": bool(regime.weaving_boost_next_day),
        "global_accident_bonus": float(regime.global_accident_bonus),
    }


def _project_events(domain_state: SimSimState) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for event in domain_state.events:
        projected = {
            "tick": int(event.get("tick", 0)),
            "event_id": int(event.get("event_id", 0)),
            "kind": str(event.get("kind", "event")),
        }
        if event.get("room_id") is not None:
            projected["room_id"] = int(event["room_id"])
        if event.get("supervisor") is not None:
            projected["supervisor"] = str(event["supervisor"])
        if isinstance(event.get("details"), dict):
            projected["details"] = dict(event["details"])
        out.append(projected)
    return out


def _diff_by_key(*, from_items: Any, to_items: Any, key_field: str) -> List[Dict[str, Any]]:
    if not isinstance(from_items, list) or not isinstance(to_items, list):
        return []
    from_map = {item.get(key_field): item for item in from_items if isinstance(item, dict)}
    updates: List[Dict[str, Any]] = []
    for item in to_items:
        if not isinstance(item, dict):
            continue
        key = item.get(key_field)
        if key is None:
            continue
        if from_map.get(key) != item:
            updates.append(item)
    return updates


def _diff_events_append(*, from_events: Any, to_events: Any) -> List[Dict[str, Any]]:
    if not isinstance(from_events, list) or not isinstance(to_events, list):
        return []
    from_keys = {
        (int(item.get("tick", 0)), int(item.get("event_id", 0)))
        for item in from_events
        if isinstance(item, dict)
    }
    appended: List[Dict[str, Any]] = []
    for item in to_events:
        if not isinstance(item, dict):
            continue
        key = (int(item.get("tick", 0)), int(item.get("event_id", 0)))
        if key not in from_keys:
            appended.append(item)
    appended.sort(key=lambda event: (int(event.get("tick", 0)), int(event.get("event_id", 0))))
    return appended
