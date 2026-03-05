from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any


def edge_key(room_a: str, room_b: str) -> str:
    """Return a stable, JSON-friendly key for an unordered room edge."""
    return "|".join(sorted([room_a, room_b]))


@dataclass(frozen=True)
class RoomSpec:
    id: str
    throughput: float
    capacity: int
    risk: float
    quality_base: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SupervisorSpec:
    id: str
    fit: Dict[str, float]
    safety: float
    quality: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EdgeSpec:
    room_a: str
    room_b: str
    base_pair_rate: float

    @property
    def key(self) -> str:
        return edge_key(self.room_a, self.room_b)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChoiceEffects:
    brains_multiplier_delta: float = 0.0
    accident_multiplier_delta: float = 0.0
    accident_chance_add: float = 0.0
    quality_add: float = 0.0
    tension_add: float = 0.0
    worker_stat_deltas: Dict[str, float] = field(default_factory=dict)
    chaos_add: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChoiceSpec:
    id: str
    label: str
    effects: ChoiceEffects

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "effects": self.effects.to_dict(),
        }


@dataclass(frozen=True)
class EventSpec:
    id: str
    scope: str  # "room" or "pair"
    applicable: List[str]
    base_weight: float
    trigger: Optional[Dict[str, Any]]
    choices: List[ChoiceSpec]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scope": self.scope,
            "applicable": list(self.applicable),
            "base_weight": self.base_weight,
            "trigger": self.trigger,
            "choices": [choice.to_dict() for choice in self.choices],
        }


@dataclass(frozen=True)
class GameSpec:
    rooms: Dict[str, RoomSpec]
    supervisors: Dict[str, SupervisorSpec]
    edges: List[EdgeSpec]
    events: List[EventSpec]
    supervisor_pair_synergy: Dict[Tuple[str, str], int]
    shift_efficiency: float
    k_risk: float
    price_per_brain: float
    worker_conversion_rate: float
    worker_quality_bonus_scale: float
    quality_price_steps: List[Tuple[float, float]]
    room_event_rate: float
    tension_decay: float
    quality_alpha: float
    quality_beta: float
    cross_room_risk_factor: float
    accident_worker_loss_rate: float
    accident_chaos_add: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rooms": {key: room.to_dict() for key, room in self.rooms.items()},
            "supervisors": {
                key: supervisor.to_dict() for key, supervisor in self.supervisors.items()
            },
            "edges": [edge.to_dict() for edge in self.edges],
            "events": [event.to_dict() for event in self.events],
            "supervisor_pair_synergy": {
                f"{pair[0]}|{pair[1]}": value
                for pair, value in self.supervisor_pair_synergy.items()
            },
            "shift_efficiency": self.shift_efficiency,
            "k_risk": self.k_risk,
            "price_per_brain": self.price_per_brain,
            "worker_conversion_rate": self.worker_conversion_rate,
            "worker_quality_bonus_scale": self.worker_quality_bonus_scale,
            "quality_price_steps": list(self.quality_price_steps),
            "room_event_rate": self.room_event_rate,
            "tension_decay": self.tension_decay,
            "quality_alpha": self.quality_alpha,
            "quality_beta": self.quality_beta,
            "cross_room_risk_factor": self.cross_room_risk_factor,
            "accident_worker_loss_rate": self.accident_worker_loss_rate,
            "accident_chaos_add": self.accident_chaos_add,
        }


def build_default_spec() -> GameSpec:
    """Return a minimal but complete spec for end-to-end simulations."""
    rooms = {
        "security": RoomSpec("security", throughput=1.2, capacity=6, risk=0.25, quality_base=45.0),
        "conveyor": RoomSpec("conveyor", throughput=1.6, capacity=8, risk=0.2, quality_base=40.0),
        "burnin_theatre": RoomSpec(
            "burnin_theatre", throughput=1.0, capacity=5, risk=0.3, quality_base=55.0
        ),
        "cognition_brewery": RoomSpec(
            "cognition_brewery", throughput=1.1, capacity=4, risk=0.15, quality_base=60.0
        ),
        "weaving_gallery": RoomSpec(
            "weaving_gallery", throughput=0.9, capacity=4, risk=0.1, quality_base=65.0
        ),
        "brain_forge": RoomSpec("brain_forge", throughput=2.0, capacity=7, risk=0.35, quality_base=50.0),
    }

    supervisors = {
        "LIMEN": SupervisorSpec(
            "LIMEN",
            fit={
                "security": 1.1,
                "conveyor": 0.9,
                "burnin_theatre": 1.0,
                "cognition_brewery": 0.8,
                "weaving_gallery": 0.9,
                "brain_forge": 1.0,
            },
            safety=0.7,
            quality=5.0,
        ),
        "STILETTO": SupervisorSpec(
            "STILETTO",
            fit={
                "security": 0.9,
                "conveyor": 1.2,
                "burnin_theatre": 0.8,
                "cognition_brewery": 1.0,
                "weaving_gallery": 0.9,
                "brain_forge": 1.1,
            },
            safety=0.5,
            quality=2.0,
        ),
        "CATHEXIS": SupervisorSpec(
            "CATHEXIS",
            fit={
                "security": 0.8,
                "conveyor": 0.9,
                "burnin_theatre": 1.1,
                "cognition_brewery": 1.2,
                "weaving_gallery": 1.0,
                "brain_forge": 0.9,
            },
            safety=0.6,
            quality=6.0,
        ),
        "RIVET_WITCH": SupervisorSpec(
            "RIVET_WITCH",
            fit={
                "security": 1.0,
                "conveyor": 1.1,
                "burnin_theatre": 0.9,
                "cognition_brewery": 0.7,
                "weaving_gallery": 0.8,
                "brain_forge": 1.3,
            },
            safety=0.4,
            quality=3.0,
        ),
        "THRUM": SupervisorSpec(
            "THRUM",
            fit={
                "security": 0.9,
                "conveyor": 0.8,
                "burnin_theatre": 1.2,
                "cognition_brewery": 1.1,
                "weaving_gallery": 1.3,
                "brain_forge": 0.7,
            },
            safety=0.8,
            quality=7.0,
        ),
        "FORGE_UNKNOWN": SupervisorSpec(
            "FORGE_UNKNOWN",
            fit={
                "security": 1.0,
                "conveyor": 1.0,
                "burnin_theatre": 1.0,
                "cognition_brewery": 0.9,
                "weaving_gallery": 0.9,
                "brain_forge": 1.4,
            },
            safety=0.3,
            quality=1.0,
        ),
    }

    edges = [
        EdgeSpec("security", "conveyor", base_pair_rate=0.4),
        EdgeSpec("conveyor", "burnin_theatre", base_pair_rate=0.3),
        EdgeSpec("cognition_brewery", "weaving_gallery", base_pair_rate=0.25),
    ]

    synergy_pairs = {
        ("LIMEN", "STILETTO"): 2,
        ("LIMEN", "CATHEXIS"): 1,
        ("STILETTO", "RIVET_WITCH"): -1,
        ("CATHEXIS", "THRUM"): 2,
        ("RIVET_WITCH", "FORGE_UNKNOWN"): -2,
        ("THRUM", "FORGE_UNKNOWN"): -1,
        ("LIMEN", "THRUM"): 1,
        ("STILETTO", "CATHEXIS"): -1,
    }
    supervisor_pair_synergy = {}
    for (a, b), value in synergy_pairs.items():
        supervisor_pair_synergy[(a, b)] = value
        supervisor_pair_synergy[(b, a)] = value

    events: List[EventSpec] = []

    def add_room_event(room_id: str, event_id: str, choices: List[ChoiceSpec]) -> None:
        events.append(
            EventSpec(
                id=event_id,
                scope="room",
                applicable=[room_id],
                base_weight=1.0,
                trigger=None,
                choices=choices,
            )
        )

    add_room_event(
        "security",
        "sec_lockdown",
        choices=[
            ChoiceSpec(
                id="tighten",
                label="Tighten protocols",
                effects=ChoiceEffects(
                    brains_multiplier_delta=-0.1,
                    accident_multiplier_delta=-0.2,
                    tension_add=5.0,
                    worker_stat_deltas={"obedience": 2.0},
                ),
            ),
            ChoiceSpec(
                id="loose",
                label="Loosen protocols",
                effects=ChoiceEffects(
                    brains_multiplier_delta=0.1,
                    accident_multiplier_delta=0.2,
                    tension_add=-2.0,
                    chaos_add=1.0,
                ),
            ),
        ],
    )
    add_room_event(
        "security",
        "sec_briefing",
        choices=[
            ChoiceSpec(
                id="drill",
                label="Drill the crew",
                effects=ChoiceEffects(
                    quality_add=3.0,
                    tension_add=2.0,
                    worker_stat_deltas={"obedience": 1.0},
                ),
            ),
            ChoiceSpec(
                id="skip",
                label="Skip the drill",
                effects=ChoiceEffects(
                    brains_multiplier_delta=0.05,
                    accident_chance_add=0.05,
                    chaos_add=2.0,
                ),
            ),
        ],
    )

    add_room_event(
        "conveyor",
        "conveyor_jam",
        choices=[
            ChoiceSpec(
                id="slow",
                label="Slow the line",
                effects=ChoiceEffects(
                    brains_multiplier_delta=-0.1,
                    accident_multiplier_delta=-0.1,
                    tension_add=1.0,
                ),
            ),
            ChoiceSpec(
                id="force",
                label="Force it through",
                effects=ChoiceEffects(
                    brains_multiplier_delta=0.15,
                    accident_multiplier_delta=0.2,
                    tension_add=4.0,
                    chaos_add=2.0,
                ),
            ),
        ],
    )
    add_room_event(
        "conveyor",
        "conveyor_tune",
        choices=[
            ChoiceSpec(
                id="precision",
                label="Precision tuning",
                effects=ChoiceEffects(quality_add=4.0, tension_add=2.0),
            ),
            ChoiceSpec(
                id="speed",
                label="Speed tuning",
                effects=ChoiceEffects(
                    brains_multiplier_delta=0.1,
                    quality_add=-2.0,
                    tension_add=1.0,
                ),
            ),
        ],
    )

    add_room_event(
        "burnin_theatre",
        "burnin_fumes",
        choices=[
            ChoiceSpec(
                id="ventilate",
                label="Ventilate",
                effects=ChoiceEffects(
                    accident_chance_add=-0.05,
                    brains_multiplier_delta=-0.05,
                    tension_add=-1.0,
                ),
            ),
            ChoiceSpec(
                id="push",
                label="Push through",
                effects=ChoiceEffects(
                    brains_multiplier_delta=0.1,
                    accident_chance_add=0.05,
                    chaos_add=2.0,
                    tension_add=3.0,
                ),
            ),
        ],
    )
    add_room_event(
        "burnin_theatre",
        "burnin_focus",
        choices=[
            ChoiceSpec(
                id="solo",
                label="Solo focus",
                effects=ChoiceEffects(
                    quality_add=5.0,
                    tension_add=3.0,
                    worker_stat_deltas={"ambition": 2.0},
                ),
            ),
            ChoiceSpec(
                id="ensemble",
                label="Ensemble focus",
                effects=ChoiceEffects(
                    brains_multiplier_delta=0.05,
                    tension_add=-2.0,
                    worker_stat_deltas={"obedience": 1.0},
                ),
            ),
        ],
    )

    add_room_event(
        "cognition_brewery",
        "cog_batch",
        choices=[
            ChoiceSpec(
                id="standardize",
                label="Standardize",
                effects=ChoiceEffects(
                    quality_add=3.0,
                    brains_multiplier_delta=-0.05,
                    tension_add=1.0,
                ),
            ),
            ChoiceSpec(
                id="experiment",
                label="Experiment",
                effects=ChoiceEffects(
                    quality_add=6.0,
                    accident_chance_add=0.03,
                    tension_add=4.0,
                    worker_stat_deltas={"ambition": 2.0},
                ),
            ),
        ],
    )
    add_room_event(
        "cognition_brewery",
        "cog_surge",
        choices=[
            ChoiceSpec(
                id="dampen",
                label="Dampen surge",
                effects=ChoiceEffects(
                    brains_multiplier_delta=-0.1,
                    accident_multiplier_delta=-0.1,
                    tension_add=-1.0,
                ),
            ),
            ChoiceSpec(
                id="ride",
                label="Ride the surge",
                effects=ChoiceEffects(
                    brains_multiplier_delta=0.2,
                    accident_multiplier_delta=0.1,
                    chaos_add=3.0,
                    tension_add=4.0,
                ),
            ),
        ],
    )

    add_room_event(
        "weaving_gallery",
        "weave_pattern",
        choices=[
            ChoiceSpec(
                id="intricate",
                label="Intricate pattern",
                effects=ChoiceEffects(
                    quality_add=5.0,
                    brains_multiplier_delta=-0.05,
                    tension_add=2.0,
                ),
            ),
            ChoiceSpec(
                id="simple",
                label="Simple pattern",
                effects=ChoiceEffects(
                    brains_multiplier_delta=0.05,
                    quality_add=-2.0,
                    tension_add=-1.0,
                ),
            ),
        ],
    )
    add_room_event(
        "weaving_gallery",
        "weave_rhythm",
        choices=[
            ChoiceSpec(
                id="steady",
                label="Steady rhythm",
                effects=ChoiceEffects(
                    tension_add=-2.0,
                    worker_stat_deltas={"morale": 2.0},
                ),
            ),
            ChoiceSpec(
                id="push",
                label="Push the rhythm",
                effects=ChoiceEffects(
                    brains_multiplier_delta=0.1,
                    tension_add=3.0,
                    worker_stat_deltas={"fatigue": 2.0},
                ),
            ),
        ],
    )

    add_room_event(
        "brain_forge",
        "forge_heat",
        choices=[
            ChoiceSpec(
                id="cool",
                label="Cool the forge",
                effects=ChoiceEffects(
                    accident_multiplier_delta=-0.15,
                    brains_multiplier_delta=-0.05,
                    tension_add=-1.0,
                ),
            ),
            ChoiceSpec(
                id="stoke",
                label="Stoke the forge",
                effects=ChoiceEffects(
                    brains_multiplier_delta=0.15,
                    accident_multiplier_delta=0.25,
                    chaos_add=4.0,
                    tension_add=5.0,
                ),
            ),
        ],
    )
    add_room_event(
        "brain_forge",
        "forge_calibration",
        choices=[
            ChoiceSpec(
                id="precise",
                label="Precise calibration",
                effects=ChoiceEffects(
                    quality_add=4.0,
                    brains_multiplier_delta=-0.05,
                    worker_stat_deltas={"obedience": 1.0},
                ),
            ),
            ChoiceSpec(
                id="rough",
                label="Rough calibration",
                effects=ChoiceEffects(
                    brains_multiplier_delta=0.1,
                    quality_add=-3.0,
                    tension_add=2.0,
                ),
            ),
        ],
    )

    events.extend(
        [
            EventSpec(
                id="sec_conv_sync",
                scope="pair",
                applicable=[edge_key("security", "conveyor")],
                base_weight=1.0,
                trigger=None,
                choices=[
                    ChoiceSpec(
                        id="sync_up",
                        label="Synchronize",
                        effects=ChoiceEffects(
                            brains_multiplier_delta=0.1,
                            quality_add=2.0,
                            tension_add=1.0,
                        ),
                    ),
                    ChoiceSpec(
                        id="independent",
                        label="Keep independent",
                        effects=ChoiceEffects(
                            brains_multiplier_delta=-0.05,
                            tension_add=-1.0,
                        ),
                    ),
                ],
            ),
            EventSpec(
                id="sec_conv_spill",
                scope="pair",
                applicable=[edge_key("security", "conveyor")],
                base_weight=1.0,
                trigger=None,
                choices=[
                    ChoiceSpec(
                        id="contain",
                        label="Contain the spill",
                        effects=ChoiceEffects(
                            accident_multiplier_delta=-0.2,
                            chaos_add=1.0,
                            tension_add=2.0,
                        ),
                    ),
                    ChoiceSpec(
                        id="rush_clean",
                        label="Rush the clean",
                        effects=ChoiceEffects(
                            brains_multiplier_delta=0.05,
                            accident_multiplier_delta=0.1,
                            chaos_add=3.0,
                            tension_add=4.0,
                        ),
                    ),
                ],
            ),
        ]
    )

    return GameSpec(
        rooms=rooms,
        supervisors=supervisors,
        edges=edges,
        events=events,
        supervisor_pair_synergy=supervisor_pair_synergy,
        shift_efficiency=0.9,
        k_risk=1.3,
        price_per_brain=10.0,
        worker_conversion_rate=0.05,
        worker_quality_bonus_scale=0.01,
        quality_price_steps=[(0.0, 0.9), (40.0, 1.0), (60.0, 1.1), (80.0, 1.25)],
        room_event_rate=0.6,
        tension_decay=5.0,
        quality_alpha=0.2,
        quality_beta=0.1,
        cross_room_risk_factor=1.0,
        accident_worker_loss_rate=0.1,
        accident_chaos_add=5.0,
    )
