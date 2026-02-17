from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math
import random

from .specs import GameSpec, EventSpec, ChoiceSpec, edge_key
from .state import GameState, RoomState, DayPlan, WorkerStats
from .policy import Policy


BEATS = ["09:00", "13:00", "16:30"]


@dataclass
class EventRecord:
    beat: str
    scope: str
    event_id: str
    choice_id: str
    rooms: Tuple[str, ...]
    notes: str = ""


@dataclass
class DayLedger:
    money_delta: float
    brains_produced: float
    brains_sold: float
    new_workers: int
    workers_lost: int
    chaos: float
    worker_stat_deltas: Dict[str, float]


@dataclass
class DayResult:
    end_state: GameState
    ledger: DayLedger
    event_log: List[EventRecord]


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _copy_state(state: GameState) -> GameState:
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
        for room_id, room in state.rooms.items()
    }
    worker_stats = WorkerStats(
        smartness=state.worker_stats.smartness,
        ambition=state.worker_stats.ambition,
        obedience=state.worker_stats.obedience,
        fatigue=state.worker_stats.fatigue,
        morale=state.worker_stats.morale,
    )
    return GameState(
        day_index=state.day_index,
        money=state.money,
        workers_count=state.workers_count,
        worker_stats=worker_stats,
        rooms=rooms,
        risk_meter=state.risk_meter,
        reputation=state.reputation,
    )


def weighted_choice(rng: random.Random, items: List[EventSpec], weights: List[float]) -> EventSpec:
    total = sum(weights)
    if total <= 0:
        return items[0]
    roll = rng.random() * total
    for item, weight in zip(items, weights):
        roll -= weight
        if roll <= 0:
            return item
    return items[-1]


def quality_price_multiplier(quality: float, steps: List[Tuple[float, float]]) -> float:
    multiplier = steps[0][1] if steps else 1.0
    for threshold, step_multiplier in steps:
        if quality >= threshold:
            multiplier = step_multiplier
        else:
            break
    return multiplier


def worker_quality_bonus(quality: float, scale: float) -> float:
    return max(0.5, 1.0 + (quality - 50.0) * scale)


def _event_triggered(
    event: EventSpec,
    state: GameState,
    room_ids: Tuple[str, ...],
) -> bool:
    if not event.trigger:
        return True
    trigger = event.trigger
    tension_values = [state.rooms[room_id].tension for room_id in room_ids]
    avg_tension = sum(tension_values) / max(1, len(tension_values))
    workers_values = [state.rooms[room_id].assigned_workers for room_id in room_ids]
    total_workers = sum(workers_values)
    if "tension_gt" in trigger and avg_tension <= float(trigger["tension_gt"]):
        return False
    if "tension_lt" in trigger and avg_tension >= float(trigger["tension_lt"]):
        return False
    if "workers_min" in trigger and total_workers < int(trigger["workers_min"]):
        return False
    if "day_index_min" in trigger and state.day_index < int(trigger["day_index_min"]):
        return False
    if "supervisor_is" in trigger:
        supervisor = trigger["supervisor_is"]
        if supervisor not in {state.rooms[room_id].assigned_supervisor for room_id in room_ids}:
            return False
    return True


def _apply_choice_effects(
    state: GameState,
    room_ids: Tuple[str, ...],
    choice: ChoiceSpec,
    tension_additions: Dict[str, float],
) -> float:
    effects = choice.effects
    for room_id in room_ids:
        room = state.rooms[room_id]
        room.brains_multiplier += effects.brains_multiplier_delta
        room.accident_multiplier += effects.accident_multiplier_delta
        room.accident_chance_add += effects.accident_chance_add
        room.quality_add += effects.quality_add
        tension_additions[room_id] = tension_additions.get(room_id, 0.0) + effects.tension_add
    for stat, delta in effects.worker_stat_deltas.items():
        if hasattr(state.worker_stats, stat):
            current = getattr(state.worker_stats, stat)
            setattr(state.worker_stats, stat, clamp(current + delta, 0.0, 100.0))
    return effects.chaos_add


def simulate_day(
    spec: GameSpec,
    initial_state: GameState,
    plan: DayPlan,
    policy: Policy,
    seed: int,
) -> DayResult:
    """Simulate a single day and return the end state, ledger, and event log."""
    rng = random.Random(seed)
    state = _copy_state(initial_state)
    event_log: List[EventRecord] = []

    for room_id, room in state.rooms.items():
        room.assigned_supervisor = plan.supervisor_assignment.get(room_id)
        room.assigned_workers = plan.workers_allocated.get(room_id, 0)
        room.tension = clamp(room.tension, 0.0, 100.0)
        room.brains_multiplier = 1.0
        room.accident_multiplier = 1.0
        room.accident_chance_add = 0.0
        room.quality_add = 0.0

    chaos_total = 0.0
    workers_lost = 0
    total_brains = 0.0
    total_quality_weighted = 0.0

    for beat in BEATS:
        beat_bonus: Dict[str, float] = {room_id: 1.0 for room_id in state.rooms.keys()}
        for edge in spec.edges:
            room_a = state.rooms[edge.room_a]
            room_b = state.rooms[edge.room_b]
            if room_a.assigned_workers <= 0 or room_b.assigned_workers <= 0:
                continue
            if not room_a.assigned_supervisor or not room_b.assigned_supervisor:
                continue
            synergy = spec.supervisor_pair_synergy.get(
                (room_a.assigned_supervisor, room_b.assigned_supervisor), 0
            )
            if synergy > 0:
                bonus = 1.0 + synergy * 0.05
                beat_bonus[edge.room_a] *= bonus
                beat_bonus[edge.room_b] *= bonus

        tension_additions: Dict[str, float] = {}

        for room_id, room in state.rooms.items():
            if room.assigned_workers <= 0 or not room.assigned_supervisor:
                continue
            if rng.random() > spec.room_event_rate:
                continue
            eligible = [
                event
                for event in spec.events
                if event.scope == "room"
                and room_id in event.applicable
                and _event_triggered(event, state, (room_id,))
            ]
            if not eligible:
                continue
            weights = [event.base_weight for event in eligible]
            event = weighted_choice(rng, eligible, weights)
            choice = policy.choose(event, state)
            chaos_total += _apply_choice_effects(state, (room_id,), choice, tension_additions)
            event_log.append(
                EventRecord(
                    beat=beat,
                    scope="room",
                    event_id=event.id,
                    choice_id=choice.id,
                    rooms=(room_id,),
                )
            )

        for edge in spec.edges:
            room_a = state.rooms[edge.room_a]
            room_b = state.rooms[edge.room_b]
            if room_a.assigned_workers <= 0 or room_b.assigned_workers <= 0:
                continue
            if not room_a.assigned_supervisor or not room_b.assigned_supervisor:
                continue
            synergy = spec.supervisor_pair_synergy.get(
                (room_a.assigned_supervisor, room_b.assigned_supervisor), 0
            )
            pair_rate = edge.base_pair_rate * (1.0 + max(0, -synergy) / 2.0)
            if rng.random() > pair_rate:
                continue
            edge_id = edge.key
            eligible = [
                event
                for event in spec.events
                if event.scope == "pair"
                and edge_id in event.applicable
                and _event_triggered(event, state, (edge.room_a, edge.room_b))
            ]
            if not eligible:
                continue
            weights = [event.base_weight for event in eligible]
            event = weighted_choice(rng, eligible, weights)
            choice = policy.choose(event, state)
            chaos_total += _apply_choice_effects(
                state, (edge.room_a, edge.room_b), choice, tension_additions
            )
            event_log.append(
                EventRecord(
                    beat=beat,
                    scope="pair",
                    event_id=event.id,
                    choice_id=choice.id,
                    rooms=(edge.room_a, edge.room_b),
                )
            )

        for room_id, room in state.rooms.items():
            tension_delta = tension_additions.get(room_id, 0.0) - spec.tension_decay
            room.tension = clamp(room.tension + tension_delta, 0.0, 100.0)

        for room_id, room in state.rooms.items():
            if room.assigned_workers <= 0 or not room.assigned_supervisor:
                continue
            room_spec = spec.rooms[room_id]
            supervisor = spec.supervisors[room.assigned_supervisor]
            base_brains = (
                room_spec.throughput
                * room.assigned_workers
                * supervisor.fit.get(room_id, 1.0)
                * spec.shift_efficiency
            )
            brains = base_brains * room.brains_multiplier * beat_bonus.get(room_id, 1.0)
            quality = (
                room_spec.quality_base
                + supervisor.quality
                + (state.worker_stats.smartness - 50.0) * spec.quality_alpha
                - state.worker_stats.fatigue * spec.quality_beta
                + room.quality_add
            )
            quality = clamp(quality, 0.0, 100.0)
            total_brains += brains
            total_quality_weighted += brains * quality

            load_factor = 0.0
            if room_spec.capacity > 0:
                load_factor = room.assigned_workers / room_spec.capacity
            accident_chance = (
                room_spec.risk
                * (load_factor ** spec.k_risk)
                * (1.0 - supervisor.safety)
                * (1.0 + room.tension / 100.0)
                * spec.cross_room_risk_factor
            )
            accident_chance = accident_chance * room.accident_multiplier + room.accident_chance_add
            accident_chance = clamp(accident_chance, 0.0, 1.0)
            if rng.random() < accident_chance:
                losses = int(math.ceil(room.assigned_workers * spec.accident_worker_loss_rate))
                losses = max(1, losses)
                losses = min(losses, room.assigned_workers)
                room.assigned_workers -= losses
                workers_lost += losses
                chaos_total += spec.accident_chaos_add
                event_log.append(
                    EventRecord(
                        beat=beat,
                        scope="accident",
                        event_id=f"accident_{room_id}",
                        choice_id="accident",
                        rooms=(room_id,),
                        notes=f"losses={losses}",
                    )
                )

    avg_quality = total_quality_weighted / total_brains if total_brains > 0 else 50.0
    if plan.production_plan == "BRAINS":
        price_multiplier = quality_price_multiplier(avg_quality, spec.quality_price_steps)
        money_delta = total_brains * spec.price_per_brain * price_multiplier
        brains_sold = total_brains
        new_workers = 0
    else:
        money_delta = 0.0
        brains_sold = 0.0
        conversion_bonus = worker_quality_bonus(avg_quality, spec.worker_quality_bonus_scale)
        new_workers = int(math.floor(total_brains * spec.worker_conversion_rate * conversion_bonus))

    state.money += money_delta
    state.workers_count = max(0, state.workers_count - workers_lost + new_workers)

    worker_stat_deltas = {
        "smartness": state.worker_stats.smartness - initial_state.worker_stats.smartness,
        "ambition": state.worker_stats.ambition - initial_state.worker_stats.ambition,
        "obedience": state.worker_stats.obedience - initial_state.worker_stats.obedience,
        "fatigue": state.worker_stats.fatigue - initial_state.worker_stats.fatigue,
        "morale": state.worker_stats.morale - initial_state.worker_stats.morale,
    }

    ledger = DayLedger(
        money_delta=money_delta,
        brains_produced=total_brains,
        brains_sold=brains_sold,
        new_workers=new_workers,
        workers_lost=workers_lost,
        chaos=chaos_total,
        worker_stat_deltas=worker_stat_deltas,
    )

    return DayResult(end_state=state, ledger=ledger, event_log=event_log)
