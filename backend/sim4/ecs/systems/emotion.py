# emotion.py (Million Dollar Version)
import random
from ..components import EmotionalState, CognitiveState, SocialState, Perception
from ...ecs.entity import EntityID


# Emotion homeostasis constants
VALENCE_DECAY = 0.1
AROUSAL_DECAY = 0.05
TENSION_DECAY = 0.08

RANDOM_DRIFT = 0.02
RELATION_INFLUENCE = 0.15
NOVELTY_PULSE = 0.25


def emotion_system(world, dt):
    """
    Million-Dollar Emotion System:
    -------------------------------
    - EntityID-safe
    - Homeostatic emotional regulation (valence, arousal, tension)
    - Cognitive emotions (curiosity/confusion) modulate arousal/tension
    - Social relationships bias valence
    - Novel/new stimuli create emotional spikes
    - Random drift prevents emotional deadlock
    - Entire system is stable for long-running simulations
    """

    for ent, (emo, cog, p, social) in world.query(
            EmotionalState, CognitiveState, Perception, SocialState):

        # --------------------------------------------------------------
        # 1. Base emotional decay toward neutral
        # --------------------------------------------------------------
        emo.valence += -VALENCE_DECAY * emo.valence * dt
        emo.arousal += -AROUSAL_DECAY * emo.arousal * dt
        emo.tension += -TENSION_DECAY * emo.tension * dt

        # --------------------------------------------------------------
        # 2. Cognitive influence: curiosity and confusion
        # --------------------------------------------------------------
        emo.arousal += (0.25 * cog.curiosity) * dt
        emo.tension += (0.15 * cog.confusion) * dt

        # --------------------------------------------------------------
        # 3. Social bias: if focusing on someone, emotional gradient
        # --------------------------------------------------------------
        if cog.focus_entity:
            target = cog.focus_entity
            affinity = social.relationships.get(target, 0.0)

            # Positive affinity -> valence ↑
            # Negative affinity -> valence ↓ + tension ↑
            emo.valence += RELATION_INFLUENCE * affinity * dt
            emo.tension += RELATION_INFLUENCE * (-affinity) * dt

        # --------------------------------------------------------------
        # 4. Novelty detection: new items in perception cause spikes
        # --------------------------------------------------------------
        if p.visible_entities:
            # Spike based on how much changed from last tick
            num_entities = len(p.visible_entities)
            novelty = random.random() < (min(1, num_entities * 0.05))
            if novelty:
                emo.arousal += NOVELTY_PULSE * dt

        # --------------------------------------------------------------
        # 5. Random drift for emergent, non-robotic behavior
        # --------------------------------------------------------------
        emo.valence += random.gauss(0, RANDOM_DRIFT) * dt
        emo.tension += random.gauss(0, RANDOM_DRIFT) * dt

        # --------------------------------------------------------------
        # 6. Bounds
        # --------------------------------------------------------------
        emo.valence = clamp(emo.valence, -1.0, 1.0)
        emo.arousal = clamp(emo.arousal, 0.0, 2.0)
        emo.tension = clamp(emo.tension, 0.0, 2.0)


# Utility
def clamp(x, lo, hi):
    return max(lo, min(hi, x))
