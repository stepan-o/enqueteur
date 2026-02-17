from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Any

from .specs import GameSpec


@dataclass
class WorkerStats:
    smartness: float
    ambition: float
    obedience: float
    fatigue: float = 0.0
    morale: float = 50.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "smartness": self.smartness,
            "ambition": self.ambition,
            "obedience": self.obedience,
            "fatigue": self.fatigue,
            "morale": self.morale,
        }


@dataclass
class RoomState:
    room_id: str
    assigned_supervisor: Optional[str] = None
    assigned_workers: int = 0
    tension: float = 0.0
    brains_multiplier: float = 1.0
    accident_multiplier: float = 1.0
    accident_chance_add: float = 0.0
    quality_add: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_id": self.room_id,
            "assigned_supervisor": self.assigned_supervisor,
            "assigned_workers": self.assigned_workers,
            "tension": self.tension,
            "brains_multiplier": self.brains_multiplier,
            "accident_multiplier": self.accident_multiplier,
            "accident_chance_add": self.accident_chance_add,
            "quality_add": self.quality_add,
        }


@dataclass
class GameState:
    day_index: int
    money: float
    workers_count: int
    worker_stats: WorkerStats
    rooms: Dict[str, RoomState]
    risk_meter: float = 0.0
    reputation: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day_index": self.day_index,
            "money": self.money,
            "workers_count": self.workers_count,
            "risk_meter": self.risk_meter,
            "reputation": self.reputation,
            "worker_stats": self.worker_stats.to_dict(),
            "rooms": {key: room.to_dict() for key, room in self.rooms.items()},
        }


@dataclass
class DayPlan:
    supervisor_assignment: Dict[str, str]
    workers_allocated: Dict[str, int]
    production_plan: str  # "BRAINS" or "WORKERS"


def default_state(spec: GameSpec, day_index: int = 1) -> GameState:
    """Create a basic starting state for simulations."""
    rooms = {room_id: RoomState(room_id=room_id) for room_id in spec.rooms.keys()}
    return GameState(
        day_index=day_index,
        money=0.0,
        workers_count=24,
        worker_stats=WorkerStats(smartness=55.0, ambition=50.0, obedience=50.0, fatigue=5.0, morale=50.0),
        rooms=rooms,
        risk_meter=0.0,
        reputation=0.0,
    )
