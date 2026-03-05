from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .specs import ChoiceSpec, EventSpec, ChoiceEffects
from .state import GameState


def _effect_value(effects: ChoiceEffects, key: str) -> float:
    return getattr(effects, key, 0.0) or 0.0


def _stat_delta(effects: ChoiceEffects, stat: str) -> float:
    return effects.worker_stat_deltas.get(stat, 0.0)


@dataclass(frozen=True)
class Policy:
    name: str

    def choose(self, event: EventSpec, state: GameState) -> ChoiceSpec:
        raise NotImplementedError


@dataclass(frozen=True)
class SafetyFirstPolicy(Policy):
    def choose(self, event: EventSpec, state: GameState) -> ChoiceSpec:
        choices = list(event.choices)
        def sort_key(choice: ChoiceSpec) -> tuple:
            effects = choice.effects
            accident_score = _effect_value(effects, "accident_multiplier_delta") + _effect_value(
                effects, "accident_chance_add"
            )
            chaos_score = _effect_value(effects, "chaos_add")
            tension_score = _effect_value(effects, "tension_add")
            return (accident_score, chaos_score, tension_score, choice.id)
        return sorted(choices, key=sort_key)[0]


@dataclass(frozen=True)
class GreedPolicy(Policy):
    def choose(self, event: EventSpec, state: GameState) -> ChoiceSpec:
        choices = list(event.choices)
        def sort_key(choice: ChoiceSpec) -> tuple:
            brains = _effect_value(choice.effects, "brains_multiplier_delta")
            return (-brains, choice.id)
        return sorted(choices, key=sort_key)[0]


@dataclass(frozen=True)
class QualityPolicy(Policy):
    def choose(self, event: EventSpec, state: GameState) -> ChoiceSpec:
        choices = list(event.choices)
        def sort_key(choice: ChoiceSpec) -> tuple:
            quality = _effect_value(choice.effects, "quality_add")
            return (-quality, choice.id)
        return sorted(choices, key=sort_key)[0]


@dataclass(frozen=True)
class ObediencePolicy(Policy):
    def choose(self, event: EventSpec, state: GameState) -> ChoiceSpec:
        choices = list(event.choices)
        def sort_key(choice: ChoiceSpec) -> tuple:
            obedience = _stat_delta(choice.effects, "obedience")
            ambition = _stat_delta(choice.effects, "ambition")
            return (-obedience, ambition, choice.id)
        return sorted(choices, key=sort_key)[0]


@dataclass(frozen=True)
class TensionSmoothingPolicy(Policy):
    def choose(self, event: EventSpec, state: GameState) -> ChoiceSpec:
        choices = list(event.choices)
        def sort_key(choice: ChoiceSpec) -> tuple:
            tension = _effect_value(choice.effects, "tension_add")
            chaos = _effect_value(choice.effects, "chaos_add")
            return (tension, chaos, choice.id)
        return sorted(choices, key=sort_key)[0]


def default_policies() -> List[Policy]:
    """Return the standard set of policies."""
    return [
        SafetyFirstPolicy("safety_first"),
        GreedPolicy("greed"),
        QualityPolicy("quality"),
        ObediencePolicy("obedience"),
        TensionSmoothingPolicy("tension_smoothing"),
    ]
