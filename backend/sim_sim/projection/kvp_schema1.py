from __future__ import annotations

"""Project sim_sim domain state to KVP sim_sim_1 viewer state."""

from typing import Any, Dict, Iterable, List, Sequence

from backend.sim4.integration.canonicalize import canonicalize_state_obj
from backend.sim4.integration.diff_ops import compute_state_diff_ops
from backend.sim4.integration.manifest_schema import ALLOWED_CHANNELS
from backend.sim4.integration.step_hash import compute_step_hash

from backend.sim_sim.kernel.state import ROOM_IDS, SimSimState, SUPERVISOR_IDS


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


def project_state_schema1(domain_state: SimSimState, channels: Sequence[str]) -> Dict[str, Any]:
    channels_norm = normalize_channels(channels)
    state: Dict[str, Any] = {}

    if "WORLD" in channels_norm:
        state["rooms"] = _project_rooms(domain_state)
        state["objects"] = []
        state["world"] = {
            "factory_input": 0.0,
            "day_index": int(domain_state.day_tick),
            "ticks_per_day": 1,
            "tick_in_day": 0,
            "time_of_day": 1.0,
            "day_phase": "day_end",
            "phase_progress": 1.0,
        }

    if "AGENTS" in channels_norm:
        state["agents"] = _project_agents(domain_state)

    if "ITEMS" in channels_norm:
        state["items"] = []

    if "EVENTS" in channels_norm:
        state["events"] = list(domain_state.events)

    if "DEBUG" in channels_norm:
        state["debug"] = {
            "sim_mode": "sim_sim_placeholder",
        }

    return canonicalize_state_obj(state)


def make_snapshot_payload(
    *,
    tick: int,
    domain_state: SimSimState,
    channels: Sequence[str],
) -> Dict[str, Any]:
    state = project_state_schema1(domain_state, channels)
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
) -> Dict[str, Any]:
    if int(to_tick) != int(from_tick) + 1:
        raise ValueError("to_tick must equal from_tick + 1")
    can_from = project_state_schema1(previous_state, channels)
    can_to = project_state_schema1(next_state, channels)
    ops = compute_state_diff_ops(can_from, can_to)
    step_hash = compute_step_hash(can_to)
    return {
        "schema_version": SIM_SIM_SCHEMA_VERSION,
        "from_tick": int(from_tick),
        "to_tick": int(to_tick),
        "prev_step_hash": str(prev_step_hash),
        "ops": ops,
        "step_hash": step_hash,
    }


def compute_step_hash_for_channels(domain_state: SimSimState, channels: Sequence[str]) -> str:
    projected = project_state_schema1(domain_state, channels)
    return compute_step_hash(projected)


def _project_rooms(domain_state: SimSimState) -> List[Dict[str, Any]]:
    occupants_by_room: Dict[int, List[int]] = {room_id: [] for room_id in ROOM_IDS}
    for supervisor_id, room_id in sorted(domain_state.assignments.items()):
        occupants_by_room.setdefault(room_id, []).append(int(supervisor_id))

    rooms: List[Dict[str, Any]] = []
    for room_id in ROOM_IDS:
        zone = "locked" if room_id == 6 else "work"
        rooms.append(
            {
                "room_id": int(room_id),
                "label": f"Room {room_id}",
                "kind_code": 1 if room_id != 6 else 9,
                "occupants": sorted(occupants_by_room.get(room_id, [])),
                "items": [],
                "neighbors": list(ROOM_NEIGHBORS.get(room_id, [])),
                "tension_tier": "low",
                "highlight": room_id == 6,
                "height": 4.0,
                "bounds": dict(ROOM_BOUNDS[room_id]),
                "zone": zone,
                "level": 0,
            }
        )
    return rooms


def _project_agents(domain_state: SimSimState) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for supervisor_id in SUPERVISOR_IDS:
        room_id = int(domain_state.assignments.get(supervisor_id, 1))
        pos = _agent_position(room_id=room_id, supervisor_id=supervisor_id)
        out.append(
            {
                "agent_id": int(supervisor_id),
                "room_id": int(room_id),
                "role_code": 0,
                "generation": 0,
                "profile_traits": {},
                "identity_vector": [],
                "persona_style_vector": None,
                "drives": {},
                "emotions": {},
                "key_relationships": [],
                "active_motives": [],
                "plan": None,
                "transform": {
                    "room_id": int(room_id),
                    "x": float(pos["x"]),
                    "y": float(pos["y"]),
                },
                "action_state_code": int(domain_state.day_tick % 5),
                "durability": 1.0,
                "energy": 1.0,
                "money": 0.0,
                "smartness": 0.5,
                "toughness": 0.5,
                "obedience": 0.5,
                "factory_goal_alignment": 0.5,
                "narrative_state_ref": None,
                "cached_summary_ref": None,
            }
        )
    return out


def _agent_position(*, room_id: int, supervisor_id: int) -> Dict[str, float]:
    bounds = ROOM_BOUNDS.get(room_id, ROOM_BOUNDS[1])
    span_x = bounds["max_x"] - bounds["min_x"]
    span_y = bounds["max_y"] - bounds["min_y"]
    # Deterministic fan-out by supervisor id.
    offset_x = (supervisor_id % 3) * 0.2 + 0.2
    offset_y = ((supervisor_id + 1) % 3) * 0.2 + 0.2
    return {
        "x": bounds["min_x"] + span_x * offset_x,
        "y": bounds["min_y"] + span_y * offset_y,
    }
