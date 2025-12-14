from __future__ import annotations

"""
Runtime-side narrative DTOs (types-only stub for Sprint 7 closure).

Scope:
- Provide a minimal NarrativeTickContext dataclass that runtime will populate
  in Sprint 8 using snapshot- and history-derived data.

Rules:
- No narrative calls or engine wiring here (SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT).
- Layer purity (SOP-100): allowed to import snapshot types; no imports from
  narrative/ or integration/.
- Deterministic, primitives-only DTO shape; no logic, I/O, or RNG.
"""

from dataclasses import dataclass
from typing import Dict, List

from backend.sim4.snapshot.world_snapshot import WorldSnapshot, AgentSnapshot


@dataclass(frozen=True)
class NarrativeTickContext:
    """
    Types-only DTO for narrative consumption in Phase I (to be populated by runtime).

    Fields:
        world_snapshot: the latest WorldSnapshot at the end of the tick.
        agents: flat list of AgentSnapshot extracted from world_snapshot.
        diff_summary: compact dict derived from SnapshotDiff summarization.

    Notes:
        - This is a pure data carrier; runtime builds instances in Sprint 8.
        - No references to runtime internals or world/ECS handles.
    """

    world_snapshot: WorldSnapshot
    agents: List[AgentSnapshot]
    diff_summary: Dict[str, object]


__all__ = ["NarrativeTickContext"]
