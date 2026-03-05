from __future__ import annotations

from backend.sim4.ecs.components.drives import DriveState
from backend.sim4.ecs.components.emotion import EmotionFields


def test_drive_state_instantiation():
    drives = DriveState(
        curiosity=0.5,
        safety_drive=0.8,
        dominance_drive=0.1,
        meaning_drive=0.9,
        attachment_drive=0.6,
        novelty_drive=0.4,
        fatigue=0.2,
        comfort=0.7,
    )
    assert drives.curiosity == 0.5
    assert drives.comfort == 0.7


def test_emotion_fields_instantiation():
    emotions = EmotionFields(
        tension=0.3,
        mood_valence=-0.1,
        arousal=0.8,
        social_stress=0.2,
        excitement=0.6,
        boredom=0.1,
    )
    assert emotions.tension == 0.3
    assert emotions.boredom == 0.1
