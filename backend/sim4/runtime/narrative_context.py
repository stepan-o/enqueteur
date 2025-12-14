from __future__ import annotations

"""
Runtime ↔ Narrative DTOs (Sub‑Sprint 8.1)

Scope:
- Define all runtime-owned DTOs used to communicate with the narrative layer
  per SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT §4.
- This module contains types only. No logic, no I/O, no RNG.

Rules (SOP-100/200):
- May import snapshot DTOs; MUST NOT import narrative/ or integration/.
- Use only Rust‑portable primitives (ints, floats, bools, str, dict, list)
  and references to snapshot DTOs.
"""

from dataclasses import dataclass
from typing import Dict, List

from backend.sim4.snapshot.world_snapshot import WorldSnapshot, AgentSnapshot
from backend.sim4.world.events import WorldEvent


@dataclass
class NarrativeBudget:
    max_tokens: int
    max_ms: int
    allow_external_calls: bool
    tick_stride: int = 1  # run narrative every N ticks (>= 1)


@dataclass(frozen=True)
class NarrativeTickContext:
    tick_index: int
    dt: float
    episode_id: int
    world_snapshot: WorldSnapshot
    agent_snapshots: List[AgentSnapshot]
    recent_events: List[WorldEvent]
    diff_summary: Dict[str, object]
    narrative_budget: NarrativeBudget


@dataclass
class NarrativeTickOutput:
    substrate_suggestions: List["SubstrateSuggestion"]
    story_fragments: List["StoryFragment"]
    memory_updates: List["MemoryUpdate"]


@dataclass(frozen=True)
class SubstrateSuggestion:
    kind: str  # "PrimitiveIntent", "NarrativeStateUpdate"
    agent_id: int | None
    payload: Dict


@dataclass(frozen=True)
class StoryFragment:
    scope: str  # "tick", "agent", "room", "global"
    agent_id: int | None
    room_id: int | None
    text: str
    importance: float


@dataclass(frozen=True)
class MemoryUpdate:
    operation: str  # "UPSERT_SUMMARY", "UPSERT_EVENT", ...
    key: int
    payload: Dict


@dataclass
class NarrativeEpisodeContext:
    episode_id: int
    world_snapshot: WorldSnapshot
    episode: "StageEpisodeV2"
    history_slice: Dict  # EpisodeHistorySlice placeholder (Rust-portable dict)
    narrative_budget: NarrativeBudget


@dataclass
class NarrativeEpisodeOutput:
    summary_text: str
    character_summaries: Dict[int, str]
    key_moments: List[str]
    memory_updates: List[MemoryUpdate]


@dataclass
class NarrativeUICallContext:
    world_snapshot: WorldSnapshot
    agent_id: int | None
    room_id: int | None
    narrative_budget: NarrativeBudget


@dataclass(frozen=True)
class NarrativeUIText:
    text: str


__all__ = [
    # budgets
    "NarrativeBudget",
    # tick I/O
    "NarrativeTickContext",
    "NarrativeTickOutput",
    # outputs
    "SubstrateSuggestion",
    "StoryFragment",
    "MemoryUpdate",
    # episode/UI contexts
    "NarrativeEpisodeContext",
    "NarrativeEpisodeOutput",
    "NarrativeUICallContext",
    "NarrativeUIText",
]
