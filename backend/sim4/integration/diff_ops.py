from __future__ import annotations

"""KVP-0001 diff op helpers (v0.1).

Computes and applies ops between two canonical state dicts.
Ops follow the KVP-0001 shape:
  - {"op": "UPSERT_ROOM", "room": {...}}
  - {"op": "REMOVE_ROOM", "room_id": 1}
  - {"op": "UPSERT_AGENT", "agent": {...}}
  - {"op": "REMOVE_AGENT", "agent_id": 1}
  - {"op": "UPSERT_ITEM", "item": {...}}
  - {"op": "REMOVE_ITEM", "item_id": 1}
  - {"op": "UPSERT_EVENT", "event": {...}}
  - {"op": "REMOVE_EVENT", "event_key": {"tick": 1, "event_id": 5}}

Ops are emitted in a deterministic order:
  ROOMS → AGENTS → ITEMS → EVENTS, with removals before upserts within each type.
"""

from typing import Any, Dict, Iterable, List, Tuple
import copy

from .canonicalize import canonicalize_state_obj, sort_rooms, sort_agents, sort_items, sort_events


def _get_field(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _index_by_id(items: Iterable[Any], field: str) -> Dict[Any, Any]:
    out: Dict[Any, Any] = {}
    for item in items:
        ident = _get_field(item, field)
        if ident is None:
            raise ValueError(f"Missing id field '{field}' in diff item")
        out[ident] = item
    return out


def _event_key(ev: Any) -> Tuple[int, int]:
    tick = _get_field(ev, "tick")
    event_id = _get_field(ev, "event_id")
    if tick is None or event_id is None:
        raise ValueError("Event is missing tick/event_id for diff key")
    return int(tick), int(event_id)


def compute_state_diff_ops(state_from: Dict[str, Any], state_to: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compute KVP diff ops between two canonical state dicts."""
    if not isinstance(state_from, dict) or not isinstance(state_to, dict):
        raise ValueError("state_from/state_to must be dicts")

    ops: List[Dict[str, Any]] = []

    def _diff_group(
        items_from: Iterable[Any],
        items_to: Iterable[Any],
        *,
        id_field: str,
        upsert_op: str,
        remove_op: str,
    ) -> None:
        map_from = _index_by_id(items_from, id_field)
        map_to = _index_by_id(items_to, id_field)

        removed_ids = sorted([i for i in map_from.keys() if i not in map_to])
        changed_ids = sorted(
            [
                i
                for i in map_to.keys()
                if (i not in map_from) or (map_to[i] != map_from[i])
            ]
        )

        for ident in removed_ids:
            ops.append({"op": remove_op, id_field: ident})
        for ident in changed_ids:
            ops.append({"op": upsert_op, upsert_op.split("_", 1)[1].lower(): copy.deepcopy(map_to[ident])})

    # Rooms
    _diff_group(
        state_from.get("rooms", []),
        state_to.get("rooms", []),
        id_field="room_id",
        upsert_op="UPSERT_ROOM",
        remove_op="REMOVE_ROOM",
    )

    # Agents
    _diff_group(
        state_from.get("agents", []),
        state_to.get("agents", []),
        id_field="agent_id",
        upsert_op="UPSERT_AGENT",
        remove_op="REMOVE_AGENT",
    )

    # Items
    _diff_group(
        state_from.get("items", []),
        state_to.get("items", []),
        id_field="item_id",
        upsert_op="UPSERT_ITEM",
        remove_op="REMOVE_ITEM",
    )

    # Events (keyed by tick+event_id)
    events_from = state_from.get("events", [])
    events_to = state_to.get("events", [])
    map_from = {_event_key(ev): ev for ev in events_from}
    map_to = {_event_key(ev): ev for ev in events_to}

    removed_keys = sorted([k for k in map_from.keys() if k not in map_to])
    changed_keys = sorted([k for k in map_to.keys() if (k not in map_from) or (map_to[k] != map_from[k])])

    for tick, event_id in removed_keys:
        ops.append({"op": "REMOVE_EVENT", "event_key": {"tick": int(tick), "event_id": int(event_id)}})
    for key in changed_keys:
        ops.append({"op": "UPSERT_EVENT", "event": copy.deepcopy(map_to[key])})

    return ops


def apply_state_diff_ops(state: Dict[str, Any], ops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply ops to a state dict and return the new canonical state."""
    if not isinstance(state, dict):
        raise ValueError("state must be a dict")
    if not isinstance(ops, list):
        raise ValueError("ops must be a list")

    new_state = copy.deepcopy(state)

    rooms = _index_by_id(new_state.get("rooms", []), "room_id") if ("rooms" in new_state) else {}
    agents = _index_by_id(new_state.get("agents", []), "agent_id") if ("agents" in new_state) else {}
    items = _index_by_id(new_state.get("items", []), "item_id") if ("items" in new_state) else {}
    events = {_event_key(ev): ev for ev in new_state.get("events", [])} if ("events" in new_state) else {}

    touched = {"rooms": False, "agents": False, "items": False, "events": False}

    for op in ops:
        if not isinstance(op, dict) or "op" not in op:
            raise ValueError("diff op must be a dict with an 'op' field")
        kind = op["op"]

        if kind == "UPSERT_ROOM":
            room = op.get("room")
            if room is None:
                raise ValueError("UPSERT_ROOM missing room payload")
            rid = _get_field(room, "room_id")
            if rid is None:
                raise ValueError("UPSERT_ROOM room missing room_id")
            rooms[rid] = room
            touched["rooms"] = True
        elif kind == "REMOVE_ROOM":
            rid = op.get("room_id")
            rooms.pop(rid, None)
            touched["rooms"] = True

        elif kind == "UPSERT_AGENT":
            agent = op.get("agent")
            if agent is None:
                raise ValueError("UPSERT_AGENT missing agent payload")
            aid = _get_field(agent, "agent_id")
            if aid is None:
                raise ValueError("UPSERT_AGENT agent missing agent_id")
            agents[aid] = agent
            touched["agents"] = True
        elif kind == "REMOVE_AGENT":
            aid = op.get("agent_id")
            agents.pop(aid, None)
            touched["agents"] = True

        elif kind == "UPSERT_ITEM":
            item = op.get("item")
            if item is None:
                raise ValueError("UPSERT_ITEM missing item payload")
            iid = _get_field(item, "item_id")
            if iid is None:
                raise ValueError("UPSERT_ITEM item missing item_id")
            items[iid] = item
            touched["items"] = True
        elif kind == "REMOVE_ITEM":
            iid = op.get("item_id")
            items.pop(iid, None)
            touched["items"] = True

        elif kind == "UPSERT_EVENT":
            ev = op.get("event")
            if ev is None:
                raise ValueError("UPSERT_EVENT missing event payload")
            events[_event_key(ev)] = ev
            touched["events"] = True
        elif kind == "REMOVE_EVENT":
            ek = op.get("event_key")
            if not isinstance(ek, dict) or "tick" not in ek or "event_id" not in ek:
                raise ValueError("REMOVE_EVENT requires event_key with tick/event_id")
            events.pop((int(ek["tick"]), int(ek["event_id"])), None)
            touched["events"] = True
        else:
            raise ValueError(f"Unknown diff op: {kind}")

    # Rebuild lists only if present or touched
    if "rooms" in new_state or touched["rooms"]:
        new_state["rooms"] = sort_rooms(list(rooms.values()))
    if "agents" in new_state or touched["agents"]:
        new_state["agents"] = sort_agents(list(agents.values()))
    if "items" in new_state or touched["items"]:
        new_state["items"] = sort_items(list(items.values()))
    if "events" in new_state or touched["events"]:
        new_state["events"] = sort_events(list(events.values()))

    return canonicalize_state_obj(new_state)


__all__ = ["compute_state_diff_ops", "apply_state_diff_ops"]
