import random
from ..components import Perception, CognitiveState

def cognition_system(world, dt):
    for ent, (p, cog) in world.query(Perception, CognitiveState):
        if p.visible_entities:
            # Pick a random visible entity to focus on
            cog.focus_entity = random.choice(p.visible_entities)
            cog.curiosity += 0.1 * dt
            cog.confusion *= 0.95
        else:
            cog.focus_entity = None
            cog.curiosity *= 0.9
            cog.confusion += 0.05 * dt
