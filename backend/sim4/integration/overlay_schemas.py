from __future__ import annotations

"""
ARTIFACTS ONLY — NO REPLAY_ — NO LIVE SESSION

Sprint 14.7 — Overlay Sidecars (Out-of-Protocol X_* Streams)

Defines typed, validated payload structures for overlay records written as
independently-decodable KVP envelopes using X_* msg_types. Overlays are never
embedded inside FULL_SNAPSHOT or FRAME_DIFF payloads.

Policies:
- schema_version must equal INTEGRATION_SCHEMA_VERSION
- UI event batches use inclusive end_tick [start_tick, end_tick]
- UI event list may be empty (sparse windows permitted)
- Events are canonically ordered by (tick, event_id)
- Psycho frames are one-per-tick payloads with nodes/edges
- Nodes sorted by id; edges sorted by (src_id, dst_id, kind)
- Any floats in metrics/data are quantized Q1E3 via canonicalize.quantize_obj
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .schema_version import INTEGRATION_SCHEMA_VERSION
from .canonicalize import quantize_obj


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _require_keys(d: Dict[str, Any], keys: Tuple[str, ...], ctx: str) -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        raise ValueError(f"{ctx} missing required fields: {', '.join(missing)}")


def _sorted_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(events, key=lambda e: (int(e.get("tick", -1)), str(e.get("event_id", ""))))


@dataclass(frozen=True)
class UIEventBatch:
    schema_version: str
    start_tick: int
    end_tick: int  # inclusive
    events: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        _require(self.schema_version == INTEGRATION_SCHEMA_VERSION, "schema_version mismatch")
        _require(self.start_tick >= 0 and self.end_tick >= self.start_tick, "invalid tick window")
        # Allow empty events for sparse windows
        ev = [
            {
                "tick": int(e["tick"]),
                "event_id": e["event_id"],
                "kind": e["kind"],
                "data": quantize_obj(e.get("data", {})),
            }
            for e in _sorted_events(self.events)
        ]
        # Validate event fields
        for e in ev:
            _require(isinstance(e["tick"], int), "event.tick must be int")
            _require(isinstance(e["event_id"], (str, int)), "event_id must be str|int")
            _require(isinstance(e["kind"], str) and e["kind"], "event.kind must be non-empty str")
            _require(isinstance(e["data"], dict), "event.data must be dict")
            _require(self.start_tick <= e["tick"] <= self.end_tick, "event.tick outside batch window")
        return {
            "schema_version": self.schema_version,
            "start_tick": int(self.start_tick),
            "end_tick": int(self.end_tick),
            "events": ev,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "UIEventBatch":
        _require(isinstance(d, dict), "UIEventBatch requires dict")
        _require_keys(d, ("schema_version", "start_tick", "end_tick", "events"), "UIEventBatch")
        _require(d["schema_version"] == INTEGRATION_SCHEMA_VERSION, "schema_version mismatched")
        st = int(d["start_tick"])  # type: ignore[arg-type]
        et = int(d["end_tick"])  # type: ignore[arg-type]
        _require(et >= st and st >= 0, "invalid start/end tick")
        ev_in = d["events"]
        _require(isinstance(ev_in, list), "events must be a list")
        # Normalize, quantize data, and sort canonically
        norm: List[Dict[str, Any]] = []
        for e in ev_in:
            _require(isinstance(e, dict), "event must be dict")
            _require_keys(e, ("tick", "event_id", "kind", "data"), "event")
            tick = int(e["tick"])  # type: ignore[arg-type]
            _require(st <= tick <= et, "event.tick outside batch window")
            data = e.get("data", {})
            _require(isinstance(data, dict), "event.data must be dict")
            norm.append({
                "tick": tick,
                "event_id": e["event_id"],
                "kind": e["kind"],
                "data": quantize_obj(data),
            })
        norm = _sorted_events(norm)
        return UIEventBatch(schema_version=d["schema_version"], start_tick=st, end_tick=et, events=norm)


def _sorted_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(nodes, key=lambda n: str(n.get("id", "")))


def _sorted_edges(edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(edges, key=lambda e: (str(e.get("src_id", "")), str(e.get("dst_id", "")), str(e.get("kind", ""))))


@dataclass(frozen=True)
class PsychoFrame:
    schema_version: str
    tick: int
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        _require(self.schema_version == INTEGRATION_SCHEMA_VERSION, "schema_version mismatch")
        _require(self.tick >= 0, "tick must be >= 0")
        _require(isinstance(self.nodes, list) and isinstance(self.edges, list), "nodes/edges must be lists")
        # Quantize any numeric metrics and sort canonically
        nodes_q = [_n_normalize(n) for n in self.nodes]
        edges_q = [_e_normalize(e) for e in self.edges]
        return {
            "schema_version": self.schema_version,
            "tick": int(self.tick),
            "nodes": _sorted_nodes(nodes_q),
            "edges": _sorted_edges(edges_q),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PsychoFrame":
        _require(isinstance(d, dict), "PsychoFrame requires dict")
        _require_keys(d, ("schema_version", "tick", "nodes", "edges"), "PsychoFrame")
        _require(d["schema_version"] == INTEGRATION_SCHEMA_VERSION, "schema_version mismatched")
        tick = int(d["tick"])  # type: ignore[arg-type]
        _require(tick >= 0, "tick must be >= 0")
        _require(isinstance(d["nodes"], list) and isinstance(d["edges"], list), "nodes/edges must be lists")
        nodes_q = [_n_normalize(n) for n in d["nodes"]]
        edges_q = [_e_normalize(e) for e in d["edges"]]
        return PsychoFrame(schema_version=d["schema_version"], tick=tick, nodes=_sorted_nodes(nodes_q), edges=_sorted_edges(edges_q))


def _n_normalize(n: Dict[str, Any]) -> Dict[str, Any]:
    _require(isinstance(n, dict), "node must be dict")
    _require("id" in n, "node.id required")
    data = n.get("data")
    if data is None:
        return {"id": n["id"], "data": {}}
    _require(isinstance(data, dict), "node.data must be dict if present")
    return {"id": n["id"], "data": quantize_obj(data)}


def _e_normalize(e: Dict[str, Any]) -> Dict[str, Any]:
    _require(isinstance(e, dict), "edge must be dict")
    _require_keys(e, ("src_id", "dst_id", "kind"), "edge")
    data = e.get("data")
    if data is None:
        data = {}
    else:
        _require(isinstance(data, dict), "edge.data must be dict if present")
        data = quantize_obj(data)
    return {"src_id": e["src_id"], "dst_id": e["dst_id"], "kind": e["kind"], "data": data}


__all__ = [
    "UIEventBatch",
    "PsychoFrame",
]
