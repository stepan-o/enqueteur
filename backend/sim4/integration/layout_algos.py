from __future__ import annotations

"""
Sprint 12.2 — Deterministic layout algorithm (placeholder city map)

This module provides a primitives-only, integration-layer room layout function
that assigns world_x, world_y, and z_layer to rooms deterministically.

Guardrails:
- Pure functions only; no I/O, clocks, RNG, or external libs (SOP-200).
- No imports from runtime/ecs/world (SOP-100).
- Results depend only on room identities and navgraph topology.
- Explicit sorting everywhere; independent of insertion order.
- All floats are quantized using integration.util.quantize.qf.

Layout modes:
 A) Navgraph present:
    - Choose canonical root = smallest room_id in each connected component.
    - BFS traversal with neighbor order sorted by room_id.
    - z_layer = BFS depth. Each depth occupies a deterministic row.
    - Within a depth, rooms are ordered by room_id.
    - Disconnected components are laid out left-to-right in ascending order of
      each component's smallest room_id. No mirroring or flipping.

 B) Navgraph missing or stub:
    - Place rooms in sorted room_id order on a deterministic fixed-column grid
      (constant column count) so that adding unrelated rooms does not move
      earlier ones.

Disconnected components:
- Components are packed side-by-side with fixed horizontal gaps so they do not
  overlap. Component packing order is deterministic (by smallest room_id).

Determinism note:
- We avoid Python's hash() influence by never using dict iteration order and by
  sorting all identity sets explicitly. No randomization. Quantization via qf.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .util.quantize import qf


# Lightweight identity-like structure (Protocol not required at runtime)
@dataclass(frozen=True)
class RoomIdentityLike:
    room_id: int | str


# NavGraphLike is represented as adjacency: dict[room_id, list[room_id]]
NavGraphLike = Dict[int | str, Sequence[int | str]]


def _id_key(room_id: int | str) -> Tuple[int, int | str]:
    """Deterministic ordering key for ids: numeric first, then strings."""
    if isinstance(room_id, int):
        return (0, room_id)
    try:
        # Strings that can represent ints should still be ordered after ints
        return (1, str(room_id))
    except Exception:
        return (1, room_id)  # type: ignore[return-value]


def _sorted_ids(ids: Iterable[int | str]) -> List[int | str]:
    return sorted(ids, key=_id_key)


def _build_graph(rooms: list[RoomIdentityLike], navgraph: Optional[NavGraphLike]) -> Dict[int | str, List[int | str]]:
    """Return adjacency limited to provided rooms. Missing navgraph → empty adjacency."""
    room_ids = {r.room_id for r in rooms}
    adj: Dict[int | str, List[int | str]] = {rid: [] for rid in room_ids}
    if not navgraph:
        return adj
    for rid, nbrs in navgraph.items():
        if rid not in room_ids:
            continue
        kept = [n for n in nbrs if n in room_ids]
        kept = _sorted_ids(kept)
        adj[rid] = kept
    # Ensure all rooms are present as keys
    for rid in room_ids:
        adj.setdefault(rid, [])
        # Sort neighbor lists deterministically
        adj[rid] = _sorted_ids(adj[rid])
    return adj


def _components(adj: Dict[int | str, List[int | str]]) -> List[List[int | str]]:
    """Return list of connected components (each a sorted list of room_ids)."""
    unseen = set(adj.keys())
    comps: List[List[int | str]] = []
    while unseen:
        # Canonical seed = smallest id from remaining
        start = min(unseen, key=_id_key)
        stack = [start]
        comp: List[int | str] = []
        unseen.remove(start)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj.get(u, []):
                if v in unseen:
                    unseen.remove(v)
                    stack.append(v)
        comp.sort(key=_id_key)
        comps.append(comp)
    # Order components by their smallest id
    comps.sort(key=lambda c: _id_key(c[0]))
    return comps


def _bfs_layers(component_nodes: List[int | str], adj: Dict[int | str, List[int | str]]) -> Dict[int | str, int]:
    """Compute BFS depth (layer) for each node, starting from canonical root (smallest id)."""
    if not component_nodes:
        return {}
    root = min(component_nodes, key=_id_key)
    from collections import deque

    layer: Dict[int | str, int] = {root: 0}
    dq = deque([root])
    while dq:
        u = dq.popleft()
        d = layer[u]
        for v in adj.get(u, []):
            if v not in layer:
                layer[v] = d + 1
                dq.append(v)
    # For disconnected ordering within component (shouldn't happen here), default zeros
    for n in component_nodes:
        layer.setdefault(n, 0)
    return layer


def layout_rooms(
    rooms: list[RoomIdentityLike],
    navgraph: Optional[NavGraphLike],
    *,
    room_width: float,
    room_height: float,
    gap_x: float,
    gap_y: float,
) -> dict[int | str, tuple[float, float, int]]:
    """Deterministic layout for rooms.

    Returns mapping: room_id -> (world_x, world_y, z_layer).

    Invariants and guarantees:
    - Same inputs → identical outputs across runs (deterministic order and math).
    - Independent of input order; explicit sorting is applied.
    - Quantization: all float outputs are quantized via qf.
    - No mirroring/rotation ambiguity: orientation is canonical L→R, top→down.
    - Adding an unrelated room does not change prior placements:
       • Graph mode: affects only within its component; components packed side-by-side.
       • Grid mode: fixed column count ensures prior indices stay the same.
    """

    # Normalize and sort rooms by id
    rooms_sorted = sorted(rooms, key=lambda r: _id_key(r.room_id))

    # Quantize geometry inputs once (deterministic)
    W = qf(float(room_width))
    H = qf(float(room_height))
    GX = qf(float(gap_x))
    GY = qf(float(gap_y))

    if navgraph:
        # Graph mode: layout by BFS layers per component, pack components horizontally
        adj = _build_graph(rooms_sorted, navgraph)
        comps = _components(adj)
        out: dict[int | str, tuple[float, float, int]] = {}

        # Track horizontal offset for components; each component width = max nodes in any layer
        x_offset_units = 0
        for comp in comps:
            layers = _bfs_layers(comp, adj)
            # group nodes by depth
            by_depth: Dict[int, List[int | str]] = {}
            for n, d in layers.items():
                by_depth.setdefault(d, []).append(n)
            depths_sorted = sorted(by_depth.keys())
            # Ensure deterministic order within depth
            for d in depths_sorted:
                by_depth[d].sort(key=_id_key)
            comp_width_units = max((len(by_depth[d]) for d in depths_sorted), default=1)

            # Place nodes: each depth is a row; within row, order by id
            for d in depths_sorted:
                row_nodes = by_depth[d]
                for i, rid in enumerate(row_nodes):
                    x_units = x_offset_units + i
                    y_units = d
                    x = qf(x_units * (W + GX))
                    y = qf(y_units * (H + GY))
                    out[rid] = (x, y, int(d))

            # Advance component offset with at least one gap column between comps
            x_offset_units += comp_width_units + 1
        return out

    else:
        # Grid mode: place in sorted order with a fixed column count for stability
        FIXED_COLS = 8  # constant to avoid shifting previous placements when count changes
        out: dict[int | str, tuple[float, float, int]] = {}
        for idx, r in enumerate(rooms_sorted):
            col = idx % FIXED_COLS
            row = idx // FIXED_COLS
            x = qf(col * (W + GX))
            y = qf(row * (H + GY))
            out[r.room_id] = (x, y, 0)  # z_layer=0 in grid mode
        return out


__all__ = ["RoomIdentityLike", "NavGraphLike", "layout_rooms"]
