# intention.py (Million Dollar Version)
import random
from ..components import CognitiveState, IntentState, EmotionalState, Perception
from ...ecs.entity import EntityID


def intention_system(world, dt):
    """
    Million-dollar intention system:
    - Emotion + cognition drive global intention
    - If agent is tense, it may avoid or freeze
    - If agent is curious, it approaches or investigates
    - If agent is neutral and unfocused, it wanders
    """

    for ent, (cog, intent, emo, p) in world.query(
            CognitiveState, IntentState, EmotionalState, Perception):

        # --------------------------------------------------------------
        # 1. If no perception, default to wander/idling
        # --------------------------------------------------------------
        if not p.visible_entities:
            if emo.arousal > 0.6:
                intent.intent = "wander"
                intent.strength = emo.arousal
            else:
                intent.intent = "idle"
                intent.strength = 0.0
            continue

        # --------------------------------------------------------------
        # 2. High tension → avoid or freeze
        # --------------------------------------------------------------
        if emo.tension > 1.2:
            if random.random() < 0.3:
                intent.intent = "freeze"
                intent.strength = emo.tension
            else:
                intent.intent = "avoid"
                intent.strength = emo.tension
            continue

        # --------------------------------------------------------------
        # 3. If agent has a focus target
        # --------------------------------------------------------------
        if cog.focus_entity:
            # Valence biases approach vs avoid
            if emo.valence >= 0:      # positive emotional state
                intent.intent = "approach"
                intent.strength = min(1.0, cog.curiosity + emo.valence)
            else:                     # negative emotional state
                intent.intent = "avoid"
                intent.strength = min(1.0, -emo.valence)
            continue

        # --------------------------------------------------------------
        # 4. If neutral but curious → investigate a random entity
        # --------------------------------------------------------------
        if cog.curiosity > 0.3:
            intent.intent = "investigate"
            intent.strength = cog.curiosity
            continue

        # --------------------------------------------------------------
        # 5. Default fallback
        # --------------------------------------------------------------
        intent.intent = "idle"
        intent.strength = 0.0
