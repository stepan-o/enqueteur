import random
from ..components import EmotionalState, CognitiveState

def emotion_system(world, dt):
    for ent, (emo, cog) in world.query(EmotionalState, CognitiveState):

        # Curiosity increases arousal
        emo.arousal += 0.2 * cog.curiosity * dt

        # Confusion increases tension
        emo.tension += 0.1 * cog.confusion * dt

        # Random small drift
        emo.valence += random.uniform(-0.05, 0.05) * dt

        # Clamp values
        emo.valence = max(-1, min(1, emo.valence))
        emo.arousal = max(0, min(1, emo.arousal))
        emo.tension = max(0, min(1, emo.tension))
