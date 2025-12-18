from __future__ import annotations

"""
Runtime ↔ Narrative DTOs and bridge (Sub‑Sprints 8.1–8.2)

Scope:
- Define all runtime-owned DTOs used to communicate with the narrative layer
  per SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT §4.
- Provide a minimal NarrativeRuntimeContext bridge that constructs a
  NarrativeTickContext and calls a narrative engine interface, while remaining
  inert (no ECS/world mutations; logging-only via history).

Rules (SOP-100/200):
- DTOs may import snapshot DTOs; MUST NOT import narrative/ or integration/.
- Bridge remains pure orchestrator: no RNG, no wall-clock, no I/O.
- Use only Rust‑portable primitives and snapshot DTOs.
"""

from dataclasses import dataclass
from typing import Dict, List, Protocol, runtime_checkable, Optional, Any, TYPE_CHECKING

from backend.sim4.snapshot.world_snapshot import WorldSnapshot, AgentSnapshot
from backend.sim4.world.events import WorldEvent
from backend.sim4.snapshot import build_world_snapshot

if TYPE_CHECKING:  # avoid import-time cycles; used for type hints only
    from backend.sim4.world.context import WorldContext
    from backend.sim4.ecs.world import ECSWorld


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


@runtime_checkable
class NarrativeEngineInterface(Protocol):
    def run_tick_jobs(self, ctx: "NarrativeTickContext") -> "NarrativeTickOutput": ...
    def summarize_episode(self, ctx: "NarrativeEpisodeContext") -> "NarrativeEpisodeOutput": ...
    def describe_scene(self, ctx: "NarrativeUICallContext") -> "NarrativeUIText": ...


@runtime_checkable
class HistoryBuffer(Protocol):
    def get_diff_summary_for_tick(self, tick_index: int, episode_id: int) -> Dict[str, Any]: ...

    def record_narrative_tick_output(
        self, *, tick_index: int, episode_id: int, output: "NarrativeTickOutput"
    ) -> None: ...

    def record_bubble_events(
        self, *, tick_index: int, episode_id: int, events: list["BubbleEvent"]
    ) -> None: ...


@dataclass
class NarrativeBudgetConfig:
    enabled: bool = True
    tick_stride: int = 1
    max_tokens_per_tick: int = 0
    max_ms_per_tick: int = 0


class NarrativeRuntimeContext:
    def __init__(
        self,
        engine: NarrativeEngineInterface,
        history: HistoryBuffer,
        budget_config: NarrativeBudgetConfig,
    ) -> None:
        self._engine = engine
        self._history = history
        self._budget_config = budget_config

    def build_tick_context(
        self,
        tick_index: int,
        dt: float,
        episode_id: int,
        world_ctx: "WorldContext",
        ecs_world: "ECSWorld",
    ) -> NarrativeTickContext:
        # Build latest snapshot from engine state (read-only)
        ws = build_world_snapshot(
            tick_index=tick_index, episode_id=episode_id, world_ctx=world_ctx, ecs_world=ecs_world
        )
        agent_snapshots: List[AgentSnapshot] = list(ws.agents)

        # Diff summary is owned by history; do not recompute here
        diff_summary = self._history.get_diff_summary_for_tick(tick_index=tick_index, episode_id=episode_id)

        budget = NarrativeBudget(
            max_tokens=self._budget_config.max_tokens_per_tick,
            max_ms=self._budget_config.max_ms_per_tick,
            allow_external_calls=True,
            tick_stride=self._budget_config.tick_stride,
        )

        return NarrativeTickContext(
            tick_index=tick_index,
            dt=dt,
            episode_id=episode_id,
            world_snapshot=ws,
            agent_snapshots=agent_snapshots,
            recent_events=[],  # events wiring deferred to future sub-sprint
            diff_summary=diff_summary,
            narrative_budget=budget,
        )

    def run_tick_narrative(
        self,
        tick_index: int,
        dt: float,
        episode_id: int,
        world_ctx: "WorldContext",
        ecs_world: "ECSWorld",
    ) -> None:
        # Global enable flag
        if not self._budget_config.enabled:
            return
        # Stride gating
        stride = self._budget_config.tick_stride if self._budget_config.tick_stride > 0 else 1
        if stride > 1 and (tick_index % stride) != 0:
            return

        ctx = self.build_tick_context(
            tick_index=tick_index,
            dt=dt,
            episode_id=episode_id,
            world_ctx=world_ctx,
            ecs_world=ecs_world,
        )

        try:
            output = self._engine.run_tick_jobs(ctx)
        except Exception:
            # Treat failures as no-op narrative output for robustness
            output = NarrativeTickOutput(
                substrate_suggestions=[], story_fragments=[], memory_updates=[]
            )

        # Logging only for 8.2; no ECS/world mutations here
        try:
            self._history.record_narrative_tick_output(
                tick_index=tick_index, episode_id=episode_id, output=output
            )
        except Exception:
            # History logging is best-effort; swallow to keep runtime stable
            pass

        # Produce BubbleEvents from StoryFragments and record them (best-effort)
        try:
            from backend.sim4.runtime.bubble_bridge import story_fragments_to_bubble_events

            bubble_events = story_fragments_to_bubble_events(
                tick_index=tick_index,
                fragments=output.story_fragments,
                default_duration_ticks=30,
            )
            if bubble_events:
                # Note: BubbleEvent is primitives-only; safe to store in history
                self._history.record_bubble_events(
                    tick_index=tick_index, episode_id=episode_id, events=bubble_events
                )
        except Exception:
            # Best-effort logging; never break runtime
            pass


__all__ = [
    # budgets
    "NarrativeBudget",
    "NarrativeBudgetConfig",
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
    # bridge & protocols
    "NarrativeEngineInterface",
    "HistoryBuffer",
    "NarrativeRuntimeContext",
]
