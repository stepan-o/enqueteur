from __future__ import annotations

"""
Sprint 13 — Psycho Topology Overlay (S13.1 + S13.2)

Integration-only DTOs and builder for a viewer-facing city-level psycho topology
overlay. Pure dataclasses/primitives, stable ordering, and quantized floats.

Constraints:
- No imports from runtime/, ecs/, or world/.
- Consume only snapshot-like structures already visible to integration.
- Deterministic sorting and canonical undirected edges.
- Quantize all floats at creation/builder time using integration.util.quantize.qf.

MVP metrics encoded (per-room):
- occupancy: int (default 0)
- tension_avg: float (default 0.0)
- mood_valence_avg: float (default 0.0)

Per-edge:
- kind: "adjacency"
- weight: 1.0 (constant, quantized)
- metrics may include optional tension_gradient if both rooms have tension values

Ordering:
- Nodes sorted by (kind, room_id/node_id) → we emit only kind="room" for MVP
- Edges sorted by (kind, src, dst); edges are canonicalized to (min, max)

Sampling policy:
- The builder produces a single frame for a given snapshot+tick. Exporters or
  callers may sample (e.g., every N ticks) by invoking the builder at desired
  ticks. A default version string is provided for schema evolution.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Tuple

from .util.quantize import qf


DEFAULT_METRICS_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class PsychoMetrics:
    occupancy: int = 0
    tension_avg: float = 0.0
    mood_valence_avg: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "tension_avg", qf(float(self.tension_avg)))
        object.__setattr__(self, "mood_valence_avg", qf(float(self.mood_valence_avg)))


@dataclass(frozen=True)
class PsychoNode:
    node_id: str  # e.g., "room:1"
    kind: str  # "room" | "zone" (MVP: "room")
    room_id: int | str | None
    metrics: PsychoMetrics


@dataclass(frozen=True)
class PsychoEdge:
    src: str
    dst: str
    kind: str  # "adjacency" | "social" (MVP: "adjacency")
    weight: float
    metrics: Dict[str, int | float | str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "weight", qf(float(self.weight)))
        # Quantize any float-like values in metrics deterministically
        if self.metrics:
            m2: Dict[str, int | float | str] = {}
            for k in sorted(self.metrics.keys()):  # stable order when converted to JSON
                v = self.metrics[k]
                if isinstance(v, float):
                    m2[k] = qf(v)
                else:
                    try:
                        # Some numeric-like may come as other types
                        if isinstance(v, (int,)):
                            m2[k] = v
                        else:
                            m2[k] = v  # keep as-is (str etc.)
                    except Exception:
                        m2[k] = v
            object.__setattr__(self, "metrics", m2)


@dataclass(frozen=True)
class PsychoTopologyFrame:
    tick_index: int
    metrics_schema_version: str
    nodes: List[PsychoNode]
    edges: List[PsychoEdge]


def _id_key(v: int | str) -> Tuple[int, int | str]:
    if isinstance(v, int):
        return (0, v)
    return (1, str(v))


def _room_node_id(room_id: int | str) -> str:
    return f"room:{room_id}"


def _extract_rooms(snapshot: Any) -> List[tuple[int | str, list[int | str]]]:
    """Return list of (room_id, neighbors[]) where neighbors is a sorted list.

    Works against generic snapshot-like objects; missing neighbors → [].
    """
    rooms = getattr(snapshot, "rooms", []) or []
    out: List[tuple[int | str, list[int | str]]] = []
    for r in rooms:
        rid = getattr(r, "room_id", getattr(r, "id", None))
        if rid is None:
            # skip malformed entries deterministically
            continue
        nbrs = list(getattr(r, "neighbors", []) or [])
        # Coerce neighbor ids to int where possible, else keep original
        def norm_id(x: Any) -> int | str:
            try:
                return int(x)
            except Exception:
                return str(x)

        nbrs = [norm_id(n) for n in nbrs]
        nbrs = sorted(set(nbrs), key=_id_key)
        out.append((rid, nbrs))
    # Sort rooms by id
    out.sort(key=lambda t: _id_key(t[0]))
    return out


def _extract_agent_room_ids(snapshot: Any) -> List[int | str | None]:
    agents = getattr(snapshot, "agents", []) or []
    room_ids: List[int | str | None] = []
    for a in agents:
        room_ids.append(getattr(a, "room_id", None))
    return room_ids


def _extract_agent_metric(a: Any, *paths: str) -> float | None:
    """Try multiple attribute names (including dotted) to extract a float metric."""
    for p in paths:
        parts = p.split(".")
        obj: Any = a
        ok = True
        for part in parts:
            obj = getattr(obj, part, None)
            if obj is None:
                ok = False
                break
        if ok:
            try:
                return float(obj)
            except Exception:
                pass
    return None


def _aggregate_room_metrics(snapshot: Any) -> Dict[int | str, PsychoMetrics]:
    rooms_info = _extract_rooms(snapshot)
    ids = [rid for rid, _ in rooms_info]
    # Initialize occupancy and lists for tension/mood
    occ: Dict[int | str, int] = {rid: 0 for rid in ids}
    tens_vals: Dict[int | str, List[float]] = {rid: [] for rid in ids}
    mood_vals: Dict[int | str, List[float]] = {rid: [] for rid in ids}

    agents = getattr(snapshot, "agents", []) or []
    for a in agents:
        rid = getattr(a, "room_id", None)
        if rid in occ:
            occ[rid] += 1
            t = _extract_agent_metric(a, "tension", "emotion.tension", "metrics.tension")
            if t is not None:
                tens_vals[rid].append(float(t))
            mv = _extract_agent_metric(a, "mood_valence", "emotion.mood_valence", "metrics.mood_valence")
            if mv is not None:
                mood_vals[rid].append(float(mv))

    out: Dict[int | str, PsychoMetrics] = {}
    for rid in ids:
        t_avg = sum(tens_vals[rid]) / len(tens_vals[rid]) if tens_vals[rid] else 0.0
        m_avg = sum(mood_vals[rid]) / len(mood_vals[rid]) if mood_vals[rid] else 0.0
        out[rid] = PsychoMetrics(occupancy=int(occ[rid]), tension_avg=qf(t_avg), mood_valence_avg=qf(m_avg))
    return out


def _canonical_edges(rooms_info: List[tuple[int | str, list[int | str]]], room_metrics: Dict[int | str, PsychoMetrics]) -> List[PsychoEdge]:
    # Build set of undirected pairs
    seen: set[Tuple[str, str]] = set()
    edges: List[PsychoEdge] = []
    for rid, nbrs in rooms_info:
        src = _room_node_id(rid)
        for n in nbrs:
            dst = _room_node_id(n)
            a, b = (src, dst) if src <= dst else (dst, src)
            key = (a, b)
            if a == b:
                continue
            if key in seen:
                continue
            seen.add(key)
            # Optional tension gradient if both rooms present
            t1 = room_metrics.get(rid, PsychoMetrics()).tension_avg
            t2 = room_metrics.get(n, PsychoMetrics()).tension_avg
            grad = abs(float(t1) - float(t2)) if (t1 is not None and t2 is not None) else 0.0
            metrics: Dict[str, int | float | str] = {}
            if (t1 is not None) and (t2 is not None):
                metrics["tension_gradient"] = qf(grad)
            edges.append(PsychoEdge(src=a, dst=b, kind="adjacency", weight=1.0, metrics=metrics))

    # Deterministic sort by (kind, src, dst)
    edges.sort(key=lambda e: (e.kind, e.src, e.dst))
    return edges


def build_psycho_topology(snapshot: Any, tick_index: int, metrics_schema_version: str = DEFAULT_METRICS_SCHEMA_VERSION) -> PsychoTopologyFrame:
    """Build a deterministic PsychoTopologyFrame from a world snapshot-like object.

    The snapshot is expected to expose .rooms (with room_id, neighbors[]?) and
    .agents (with room_id and optional metrics). Missing data is handled with
    defaults and will not cause crashes.
    """
    rooms_info = _extract_rooms(snapshot)
    room_metrics = _aggregate_room_metrics(snapshot)

    # Nodes: one per room
    nodes: List[PsychoNode] = []
    for rid, _ in rooms_info:
        nid = _room_node_id(rid)
        nodes.append(PsychoNode(node_id=nid, kind="room", room_id=rid, metrics=room_metrics.get(rid, PsychoMetrics())))

    # Sort nodes deterministically (kind then node_id)
    nodes.sort(key=lambda n: (n.kind, n.node_id))

    # Edges from adjacency
    edges = _canonical_edges(rooms_info, room_metrics)

    return PsychoTopologyFrame(
        tick_index=int(tick_index),
        metrics_schema_version=str(metrics_schema_version),
        nodes=nodes,
        edges=edges,
    )


__all__ = [
    "PsychoTopologyFrame",
    "PsychoNode",
    "PsychoEdge",
    "PsychoMetrics",
    "DEFAULT_METRICS_SCHEMA_VERSION",
    "build_psycho_topology",
]
