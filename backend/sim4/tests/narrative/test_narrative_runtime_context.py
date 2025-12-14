from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from backend.sim4.narrative.interface import NullNarrativeEngine
from backend.sim4.runtime.narrative_context import (
    NarrativeBudgetConfig,
    NarrativeRuntimeContext,
    NarrativeTickOutput,
)
from backend.sim4.world.context import WorldContext, RoomRecord
from backend.sim4.ecs.world import ECSWorld


class FakeHistory:
    def __init__(self) -> None:
        self.logged: List[tuple[int, int, NarrativeTickOutput]] = []
        self.diff_by_tick: Dict[tuple[int, int], Dict[str, Any]] = {}

    def get_diff_summary_for_tick(self, tick_index: int, episode_id: int) -> Dict[str, Any]:
        return self.diff_by_tick.get((tick_index, episode_id), {})

    def record_narrative_tick_output(
        self, *, tick_index: int, episode_id: int, output: NarrativeTickOutput
    ) -> None:
        self.logged.append((tick_index, episode_id, output))


def make_world() -> tuple[WorldContext, ECSWorld]:
    wc = WorldContext()
    # Minimal world with a single room to ensure non-empty rooms list is allowed
    wc.register_room(RoomRecord(id=1, label="Room A"))
    ecs = ECSWorld()
    return wc, ecs


def test_build_tick_context_happy_path():
    wc, ecs = make_world()
    history = FakeHistory()
    history.diff_by_tick[(5, 7)] = {"moved_agents": [1]}
    engine = NullNarrativeEngine()
    nrc = NarrativeRuntimeContext(
        engine=engine, history=history, budget_config=NarrativeBudgetConfig()
    )

    ctx = nrc.build_tick_context(
        tick_index=5, dt=1.0, episode_id=7, world_ctx=wc, ecs_world=ecs
    )

    # Basic shape assertions
    assert ctx.tick_index == 5
    assert ctx.episode_id == 7
    assert isinstance(ctx.diff_summary, dict)
    assert ctx.diff_summary == {"moved_agents": [1]}
    assert ctx.world_snapshot is not None
    assert isinstance(ctx.agent_snapshots, list)
    assert isinstance(ctx.recent_events, list)
    assert hasattr(ctx.narrative_budget, "max_tokens")


def test_run_tick_narrative_respects_stride():
    wc, ecs = make_world()
    calls: List[int] = []

    class RecordingEngine(NullNarrativeEngine):
        def run_tick_jobs(self, ctx):  # type: ignore[override]
            calls.append(ctx.tick_index)
            return super().run_tick_jobs(ctx)

    engine = RecordingEngine()
    history = FakeHistory()
    cfg = NarrativeBudgetConfig(enabled=True, tick_stride=2, max_tokens_per_tick=0, max_ms_per_tick=0)
    nrc = NarrativeRuntimeContext(engine=engine, history=history, budget_config=cfg)

    # Tick 1: skipped due to stride=2
    nrc.run_tick_narrative(tick_index=1, dt=1.0, episode_id=1, world_ctx=wc, ecs_world=ecs)
    # Tick 2: executed
    nrc.run_tick_narrative(tick_index=2, dt=1.0, episode_id=1, world_ctx=wc, ecs_world=ecs)

    assert calls == [2]
    assert [t for t, ep, _ in history.logged] == [2]


def test_run_tick_narrative_disabled():
    wc, ecs = make_world()

    class CountingEngine(NullNarrativeEngine):
        def __init__(self) -> None:
            self.count = 0

        def run_tick_jobs(self, ctx):  # type: ignore[override]
            self.count += 1
            return super().run_tick_jobs(ctx)

    engine = CountingEngine()
    history = FakeHistory()
    cfg = NarrativeBudgetConfig(enabled=False, tick_stride=1)
    nrc = NarrativeRuntimeContext(engine=engine, history=history, budget_config=cfg)

    nrc.run_tick_narrative(tick_index=1, dt=1.0, episode_id=1, world_ctx=wc, ecs_world=ecs)
    nrc.run_tick_narrative(tick_index=2, dt=1.0, episode_id=1, world_ctx=wc, ecs_world=ecs)

    assert engine.count == 0
    assert history.logged == []
