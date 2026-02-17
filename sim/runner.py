from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Tuple
import itertools
import math
import statistics

from .engine import simulate_day
from .state import GameState, DayPlan, RoomState, WorkerStats
from .specs import GameSpec
from .policy import Policy


@dataclass
class MetricSummary:
    mean: float
    std: float
    p10: float
    p50: float
    p90: float


@dataclass
class AggregateMetrics:
    n: int
    metrics: Dict[str, MetricSummary]

    def to_rows(self) -> List[Dict[str, float]]:
        rows: List[Dict[str, float]] = []
        for name, summary in self.metrics.items():
            rows.append(
                {
                    "metric": name,
                    "mean": summary.mean,
                    "std": summary.std,
                    "p10": summary.p10,
                    "p50": summary.p50,
                    "p90": summary.p90,
                }
            )
        return rows


@dataclass
class StrategyResult:
    plan: DayPlan
    policy_name: str
    metrics: AggregateMetrics
    score: float


def _percentile(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    if len(values_sorted) == 1:
        return values_sorted[0]
    idx = int(math.floor((percentile / 100.0) * (len(values_sorted) - 1)))
    return values_sorted[idx]


def _summarize(values: List[float]) -> MetricSummary:
    if not values:
        return MetricSummary(0.0, 0.0, 0.0, 0.0, 0.0)
    mean = statistics.fmean(values)
    std = statistics.pstdev(values) if len(values) > 1 else 0.0
    return MetricSummary(
        mean=mean,
        std=std,
        p10=_percentile(values, 10),
        p50=_percentile(values, 50),
        p90=_percentile(values, 90),
    )


def enumerate_plans(
    day_index: int,
    available_rooms: List[str],
    available_supervisors: List[str],
    workers_count: int,
    capacity_constraints: Dict[str, int],
) -> Iterator[DayPlan]:
    """Yield feasible plans for the given inputs."""
    rooms = list(available_rooms)
    if len(available_supervisors) >= len(rooms):
        supervisor_assignments = itertools.permutations(available_supervisors, len(rooms))
    else:
        supervisor_assignments = itertools.product(available_supervisors, repeat=len(rooms))

    def allocation_gen(index: int, remaining: int) -> Iterator[List[int]]:
        if index == len(rooms) - 1:
            capacity = capacity_constraints.get(rooms[index], remaining)
            if remaining <= capacity:
                yield [remaining]
            return
        capacity = capacity_constraints.get(rooms[index], remaining)
        for workers in range(0, min(capacity, remaining) + 1):
            for tail in allocation_gen(index + 1, remaining - workers):
                yield [workers] + tail

    production_plans = ["BRAINS", "WORKERS"] if day_index >= 3 else ["BRAINS"]

    for assignment in supervisor_assignments:
        supervisor_map = {room: supervisor for room, supervisor in zip(rooms, assignment)}
        for allocation in allocation_gen(0, workers_count):
            workers_map = {room: count for room, count in zip(rooms, allocation)}
            for production_plan in production_plans:
                yield DayPlan(
                    supervisor_assignment=supervisor_map,
                    workers_allocated=workers_map,
                    production_plan=production_plan,
                )


class SimulationRunner:
    """Simulation helpers bound to a specific spec and initial state."""

    def __init__(self, spec: GameSpec, initial_state: GameState) -> None:
        self.spec = spec
        self.initial_state = initial_state

    def run_monte_carlo(
        self,
        n: int,
        day_index: int,
        plan: DayPlan,
        policy: Policy,
        seed0: int,
    ) -> AggregateMetrics:
        """Run Monte Carlo simulations with sequential seeds."""
        money_values: List[float] = []
        workers_values: List[float] = []
        workers_lost_values: List[float] = []
        chaos_values: List[float] = []
        brains_values: List[float] = []

        for i in range(n):
            state = self._state_for_day(day_index)
            result = simulate_day(self.spec, state, plan, policy, seed0 + i)
            ledger = result.ledger
            money_values.append(ledger.money_delta)
            workers_values.append(ledger.new_workers)
            workers_lost_values.append(ledger.workers_lost)
            chaos_values.append(ledger.chaos)
            brains_values.append(ledger.brains_produced)

        metrics = {
            "money_delta": _summarize(money_values),
            "new_workers": _summarize(workers_values),
            "workers_lost": _summarize(workers_lost_values),
            "chaos": _summarize(chaos_values),
            "total_brains": _summarize(brains_values),
        }
        return AggregateMetrics(n=n, metrics=metrics)

    def evaluate_strategies(
        self,
        plans: Iterable[DayPlan],
        policies: Iterable[Policy],
        n_mc: int,
        seed0: int,
        day_index: int,
    ) -> List[StrategyResult]:
        """Evaluate plan/policy pairs and return a ranked table."""
        results: List[StrategyResult] = []
        for plan in plans:
            for policy in policies:
                metrics = self.run_monte_carlo(n_mc, day_index, plan, policy, seed0)
                score = metrics.metrics["money_delta"].mean
                results.append(
                    StrategyResult(
                        plan=plan,
                        policy_name=policy.name,
                        metrics=metrics,
                        score=score,
                    )
                )
        return sorted(results, key=lambda item: item.score, reverse=True)

    def _state_for_day(self, day_index: int) -> GameState:
        rooms = {
            room_id: RoomState(
                room_id=room.room_id,
                assigned_supervisor=room.assigned_supervisor,
                assigned_workers=room.assigned_workers,
                tension=room.tension,
                brains_multiplier=room.brains_multiplier,
                accident_multiplier=room.accident_multiplier,
                accident_chance_add=room.accident_chance_add,
                quality_add=room.quality_add,
            )
            for room_id, room in self.initial_state.rooms.items()
        }
        worker_stats = WorkerStats(
            smartness=self.initial_state.worker_stats.smartness,
            ambition=self.initial_state.worker_stats.ambition,
            obedience=self.initial_state.worker_stats.obedience,
            fatigue=self.initial_state.worker_stats.fatigue,
            morale=self.initial_state.worker_stats.morale,
        )
        return GameState(
            day_index=day_index,
            money=self.initial_state.money,
            workers_count=self.initial_state.workers_count,
            worker_stats=worker_stats,
            rooms=rooms,
            risk_meter=self.initial_state.risk_meter,
            reputation=self.initial_state.reputation,
        )


def run_monte_carlo(
    spec: GameSpec,
    initial_state: GameState,
    n: int,
    day_index: int,
    plan: DayPlan,
    policy: Policy,
    seed0: int,
) -> AggregateMetrics:
    """Functional wrapper for Monte Carlo simulations."""
    runner = SimulationRunner(spec, initial_state)
    return runner.run_monte_carlo(n, day_index, plan, policy, seed0)


def evaluate_strategies(
    spec: GameSpec,
    initial_state: GameState,
    plans: Iterable[DayPlan],
    policies: Iterable[Policy],
    n_mc: int,
    seed0: int,
    day_index: int,
) -> List[StrategyResult]:
    """Functional wrapper for ranking plans + policies."""
    runner = SimulationRunner(spec, initial_state)
    return runner.evaluate_strategies(plans, policies, n_mc, seed0, day_index)
