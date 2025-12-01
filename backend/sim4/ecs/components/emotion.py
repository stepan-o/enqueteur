"""Emotion field substrate component (Sprint 3.1).

Mind layer mapping: L4 (continuous affective fields, no labels).
All values are numeric; narrative/UI will map to human-readable emotions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EmotionFields:
    """
    Continuous emotion field substrate (L4).

    Narrative and UI map these numbers to human-readable emotions.
    ECS only stores numeric values.
    """

    tension: float
    mood_valence: float
    arousal: float
    social_stress: float
    excitement: float
    boredom: float
